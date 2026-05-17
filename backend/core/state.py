"""Production state manager — thread-safe, modular, resettable.

Replaces the monolithic global state dict from colab_backend.py with
a clean class-based manager that:
- Encapsulates all mutable state
- Provides atomic operations (no partial updates)
- Tracks incident counters, deduplication sets
- Supports full reset for simulation reruns
- Emits events for WebSocket broadcasting

All state mutation goes through this class — no direct dict access.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone, timedelta
from typing import Any

from data.city_graph import create_city_graph
from data.resources import load_resources
from backend.core.config import get_settings

IST = timezone(timedelta(hours=5, minutes=30))


class StateManager:
    """Thread-safe state container for CrisisGrid AI."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._settings = get_settings()
        self._initialize()

    def _initialize(self) -> None:
        """Set all state fields to their initial values."""
        self.city_graph = create_city_graph()
        self.resources: dict = load_resources()
        self.incidents: list[dict] = []
        self.dispatch_log: list[dict] = []
        self.agent_reasoning: dict[str, str] = {}
        self.alerts: list[str] = []
        self.live_feed: list[str] = []
        self.raw_calls: list[str] = []

        # Internal tracking
        self._raw_incidents: list[dict] = []
        self._raw_dispatch_log: list[dict] = []
        self._seen_incident_ids: set[str] = set()
        self._incident_counter: int = 0

        # WebSocket event queue — consumed by the ws manager
        self._pending_events: list[dict] = []

    # ── Atomic operations ──

    def reset(self) -> dict:
        """Reset all state to initial configuration. Returns confirmation."""
        with self._lock:
            self._initialize()
            self.live_feed = ["🔄 System reset — all resources restored to AVAILABLE"]
            return {
                "message": "State reset successfully",
                "resources": len(self.resources),
            }

    def next_incident_id(self) -> str:
        """Generate the next sequential incident display ID."""
        with self._lock:
            self._incident_counter += 1
            return f"INC-{self._incident_counter:03d}"

    def is_incident_seen(self, internal_id: str) -> bool:
        """Check if an incident has already been processed."""
        return internal_id in self._seen_incident_ids

    def mark_incident_seen(self, internal_id: str) -> None:
        """Mark an incident as processed (deduplication)."""
        with self._lock:
            self._seen_incident_ids.add(internal_id)

    def add_incident(self, formatted: dict, raw: dict) -> None:
        """Add a formatted incident and its raw pipeline data."""
        with self._lock:
            self.incidents.append(formatted)
            self._raw_incidents.append(raw)

    def add_dispatch_entry(self, formatted: dict, raw: dict | None = None) -> None:
        """Add a formatted dispatch log entry."""
        with self._lock:
            self.dispatch_log.append(formatted)
            if raw:
                self._raw_dispatch_log.append(raw)

    def update_resources(self, resources: dict) -> None:
        """Replace the full resource dict (from pipeline output)."""
        with self._lock:
            self.resources = resources

    def update_reasoning(self, reasoning: dict[str, str]) -> None:
        """Replace agent reasoning."""
        with self._lock:
            self.agent_reasoning = reasoning

    def append_reasoning(self, agent: str, text: str) -> None:
        """Append text to an agent's reasoning."""
        with self._lock:
            existing = self.agent_reasoning.get(agent, "")
            self.agent_reasoning[agent] = f"{existing}\n\n{text}" if existing else text

    def add_alerts(self, new_alerts: list[str]) -> list[str]:
        """Add new unique alerts. Returns the list of actually-new ones."""
        added = []
        with self._lock:
            for alert in new_alerts:
                if alert not in self.alerts:
                    self.alerts.append(alert)
                    added.append(alert)
        return added

    def add_feed_events(self, events: list[str]) -> None:
        """Prepend events to the live feed (newest first), capped."""
        with self._lock:
            self.live_feed = (events + self.live_feed)[
                : self._settings.MAX_LIVE_FEED_ENTRIES
            ]

    def add_raw_call(self, transcript: str) -> None:
        """Record a raw call transcript."""
        with self._lock:
            self.raw_calls.append(transcript)

    # ── WebSocket events ──

    def emit_event(self, event_type: str, data: Any = None) -> None:
        """Queue a WebSocket event for broadcasting."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
        }
        with self._lock:
            self._pending_events.append(event)

    def drain_events(self) -> list[dict]:
        """Pop all pending events (consumed by WebSocket manager)."""
        with self._lock:
            events = self._pending_events.copy()
            self._pending_events.clear()
            return events

    # ── Pipeline state bridge ──

    def get_pipeline_state(self) -> dict:
        """Build the state dict expected by run_pipeline_stateful().

        This bridges the new StateManager with the existing LangGraph pipeline
        which expects a flat dict with specific keys.
        """
        return {
            "resources": self.resources,
            "agent_reasoning": dict(self.agent_reasoning),
            "city_graph": self.city_graph,
            "_raw_incidents": list(self._raw_incidents),
            "_raw_dispatch_log": list(self._raw_dispatch_log),
        }

    # ── Snapshot for API responses ──

    def snapshot(self) -> dict:
        """Build a full state snapshot for API responses.

        Replaces the old _build_response() function.
        """
        res_list = []
        for uid, info in self.resources.items():
            r = {"id": uid, **info}
            for entry in self.dispatch_log:
                if entry.get("unit") == uid or entry.get("unit_id") == uid:
                    r["assigned_incident"] = entry.get("incident", "")
                    r["eta_display"] = entry.get("eta", "")
                    break
            res_list.append(r)

        total = len(self.resources)
        dispatched = sum(
            1 for u in self.resources.values() if u.get("status") == "DISPATCHED"
        )
        utilization = round(dispatched / max(total, 1), 2)

        return {
            "incidents": self.incidents,
            "resources": res_list,
            "dispatch_log": self.dispatch_log,
            "agent_reasoning": self.agent_reasoning,
            "alerts": self.alerts,
            "live_feed": self.live_feed,
            "stats": {
                "total_incidents": len(self.incidents),
                "total_dispatches": len(self.dispatch_log),
                "units_deployed": dispatched,
                "units_total": total,
                "utilization": utilization,
                "avg_severity_score": round(
                    sum(inc.get("severity_score", 0) for inc in self.incidents)
                    / max(len(self.incidents), 1),
                    1,
                ),
                "critical_count": sum(
                    1
                    for inc in self.incidents
                    if inc.get("severity", "").upper() == "CRITICAL"
                ),
                "high_count": sum(
                    1
                    for inc in self.incidents
                    if inc.get("severity", "").upper() == "HIGH"
                ),
            },
        }


# ── Singleton ──

_state_manager: StateManager | None = None


def get_state_manager() -> StateManager:
    """Return the global StateManager singleton."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
