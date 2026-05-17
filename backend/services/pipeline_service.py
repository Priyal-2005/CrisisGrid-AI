"""Pipeline service — runs the LangGraph pipeline and merges results into state.

This is the core orchestration service that:
1. Accepts a raw transcript
2. Runs it through the 4-agent LangGraph pipeline
3. Deduplicates and formats the output
4. Merges results into the persistent StateManager
5. Emits WebSocket events for realtime updates

Extracted from the monolithic _process_transcript() in colab_backend.py.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from graph.workflow import run_pipeline_stateful
from backend.core.state import StateManager
from backend.core.logging import get_logger
from backend.websocket.manager import ConnectionManager

logger = get_logger("pipeline")
IST = timezone(timedelta(hours=5, minutes=30))

# ── Type icon mapping ──

TYPE_ICON: dict[str, str] = {
    "fire": "🔥", "flood": "🌊", "earthquake": "🏚️",
    "accident": "💥", "medical": "🚑", "unknown": "⚠️",
    "explosion": "💣", "chemical_fire": "☣️", "industrial_fire": "🏭",
    "gas_leak": "⛽", "building_collapse": "🏗️", "chemical_spill": "☢️",
    "chemical_explosion": "☣️", "industrial_explosion": "🏭",
    "gas_explosion": "⛽", "toxic_release": "☠️",
}


def _get_icon(incident_type: str) -> str:
    return TYPE_ICON.get(incident_type.lower(), "⚠️")


# ── Formatting helpers (preserved from colab_backend.py) ──

def _format_incident(raw_inc: dict, display_id: str, units: list, ts: str) -> dict:
    inc_type = raw_inc.get("incident_type", raw_inc.get("type", "Unknown"))
    location = raw_inc.get("location", "Unknown")
    severity = raw_inc.get("severity", "MEDIUM").upper()
    severity_score = raw_inc.get("severity_score", 0)
    calls_merged = raw_inc.get("duplicate_count", raw_inc.get("calls_merged", 1))
    escalation = raw_inc.get("escalation_reason")
    resolved_type = raw_inc.get("resolved_type", inc_type)
    zone_risk = raw_inc.get("zone_risk", {})
    required_resources = raw_inc.get("required_resources", {})
    severity_explanation = raw_inc.get("severity_explanation", "")

    desc = raw_inc.get("summary", raw_inc.get("description",
           f"{inc_type.title()} reported at {location}"))
    if escalation:
        desc = f"{desc} [{escalation}]"

    return {
        "id": display_id,
        "internal_id": raw_inc.get("id", raw_inc.get("master_incident_id", "")),
        "type": inc_type.title(),
        "resolved_type": resolved_type,
        "location": location.replace("_", " ").title(),
        "severity": severity,
        "severity_score": severity_score,
        "status": "ACTIVE",
        "units": units,
        "time": ts,
        "timestamp": ts,
        "description": desc,
        "calls_merged": calls_merged,
        "injured_count": raw_inc.get("injured_count", 0),
        "trapped_count": raw_inc.get("trapped_count", 0),
        "resources_needed": raw_inc.get("resources_needed", []),
        "required_resources": required_resources,
        "confidence_score": raw_inc.get("confidence_score", 50),
        "escalated": escalation is not None,
        "severity_explanation": severity_explanation,
        "zone_risk": zone_risk,
        "has_chemical_hazard": raw_inc.get("has_chemical_hazard", False),
        "has_spread_risk": raw_inc.get("has_spread_risk", False),
    }


def _format_dispatch_entry(raw_entry: dict, display_inc_id: str) -> dict:
    route = raw_entry.get("route", [])
    route_str = (
        " → ".join(str(x).replace("_", " ").title() for x in route)
        if isinstance(route, list) else str(route)
    )
    eta = raw_entry.get("eta", 0)
    ts = raw_entry.get("timestamp", "")
    time_str = ts.split(" ")[1] if " " in ts else ts
    rerouted = raw_entry.get("rerouted_from")
    status = "REROUTED → EN ROUTE" if rerouted else "EN ROUTE"
    return {
        "time": time_str,
        "incident": display_inc_id,
        "incident_id": display_inc_id,
        "unit_id": raw_entry.get("unit_id", ""),
        "unit": raw_entry.get("unit_id", ""),
        "route": route_str,
        "eta": f"{eta:.0f} min" if isinstance(eta, (int, float)) else str(eta),
        "severity": raw_entry.get("severity", ""),
        "severity_score": raw_entry.get("severity_score", 0),
        "status": status,
        "rerouted_from": rerouted or "",
    }


def _humanize_reasoning(raw_reasoning: dict, context: str) -> dict:
    """Convert pipeline reasoning into human-readable explanations."""
    result = {}

    triage_raw = raw_reasoning.get("triage", "")
    result["Triage Agent"] = (
        f"📞 Incoming 112 call processed.\n{context}\n\n"
        + (triage_raw if triage_raw else "No new calls processed.")
    )

    fusion_raw = raw_reasoning.get("fusion", "")
    result["Fusion Agent"] = (
        "🔗 Duplicate analysis and incident merging:\n\n"
        + (fusion_raw if fusion_raw else "Waiting for triage output.")
    )

    dispatch_raw = raw_reasoning.get("dispatch", "")
    result["Dispatch Agent"] = (
        "🚀 Resource routing decision:\n\n"
        + (dispatch_raw if dispatch_raw else "No dispatch actions taken.")
    )

    strategy_raw = raw_reasoning.get("strategy", "")
    result["Strategy Agent"] = (
        "🧠 Strategic assessment:\n\n"
        + (strategy_raw if strategy_raw else "Awaiting dispatch data.")
    )

    return result


# ── Backend-level rerouting ──

def _attempt_backend_reroute(
    state: StateManager,
    new_inc_display_id: str,
    new_severity: str,
    resources_needed: list,
) -> dict | None:
    """Reroute a unit from a LOW incident to a CRITICAL one at the backend level."""
    if new_severity.upper() != "CRITICAL":
        return None

    for entry in state.dispatch_log:
        if entry.get("incident") == new_inc_display_id or \
           entry.get("incident_id") == new_inc_display_id:
            return None

    TYPE_MAP = {
        "fire": "fire_truck", "Fire": "fire_truck", "fire_truck": "fire_truck",
        "Fire Truck": "fire_truck", "ambulance": "ambulance", "Ambulance": "ambulance",
        "Medical": "ambulance", "medical": "ambulance", "police": "police", "Police": "police",
    }
    needed_types = set()
    for need in resources_needed:
        t = TYPE_MAP.get(need)
        if t:
            needed_types.add(t)
    if not needed_types:
        return None

    low_incidents = {
        inc["id"]: inc for inc in state.incidents
        if inc.get("severity", "LOW").upper() == "LOW"
    }
    if not low_incidents:
        return None

    for entry in reversed(state.dispatch_log):
        donor_inc_id = entry.get("incident")
        unit_id = entry.get("unit") or entry.get("unit_id")
        if donor_inc_id not in low_incidents:
            continue
        if not unit_id or unit_id not in state.resources:
            continue
        unit = state.resources[unit_id]
        if unit.get("status") != "DISPATCHED":
            continue
        if unit.get("type") not in needed_types:
            continue

        state.resources[unit_id]["status"] = "DISPATCHED"
        state.resources[unit_id]["assigned_incident"] = new_inc_display_id

        now_str = datetime.now(IST).strftime("%H:%M:%S")
        reroute_entry = {
            "time": now_str,
            "incident": new_inc_display_id,
            "incident_id": new_inc_display_id,
            "unit": unit_id,
            "unit_id": unit_id,
            "route": f"[REROUTED from {donor_inc_id}]",
            "eta": "Redirecting...",
            "severity": "CRITICAL",
            "status": "REROUTED → EN ROUTE",
            "rerouted_from": donor_inc_id,
        }
        state.add_dispatch_entry(reroute_entry)

        logger.info(
            "🔄 REROUTED %s: pulled from LOW incident %s → CRITICAL %s",
            unit_id, donor_inc_id, new_inc_display_id,
        )

        state.append_reasoning(
            "Dispatch Agent",
            f"🔄 BACKEND REROUTE: {unit_id} reassigned from "
            f"LOW incident {donor_inc_id} to CRITICAL {new_inc_display_id}. "
            f"Reason: CRITICAL incidents preempt LOW priority dispatches.",
        )

        return reroute_entry

    return None


# ── Main pipeline execution ──

async def process_transcript(
    transcript: str,
    state: StateManager,
    ws: ConnectionManager | None = None,
) -> dict:
    """Run the full LangGraph pipeline for one transcript.

    This is the core function — equivalent to the old _process_transcript().
    Runs pipeline → deduplicates → formats → merges into state → emits events.

    Args:
        transcript: Raw 112 call transcript.
        state: The StateManager instance.
        ws: Optional WebSocket manager for realtime broadcasting.

    Returns:
        Full state snapshot dict.
    """
    state.add_raw_call(transcript)

    # Run LangGraph pipeline
    pipeline_state = state.get_pipeline_state()
    result = run_pipeline_stateful(state=pipeline_state, transcript=transcript)

    now_str = datetime.now(IST).strftime("%H:%M:%S")

    # Deduplicate pipeline output
    raw_incidents = result.get("incidents", [])
    seen_this_run: set = set()
    deduped_incidents = []
    for inc in raw_incidents:
        iid = inc.get("id", inc.get("master_incident_id", ""))
        if iid and iid not in seen_this_run:
            seen_this_run.add(iid)
            deduped_incidents.append(inc)

    raw_log = result.get("dispatch_log", [])
    seen_log: set = set()
    deduped_log = []
    for entry in raw_log:
        key = (entry.get("incident_id"), entry.get("unit_id"), entry.get("timestamp"))
        if key not in seen_log:
            seen_log.add(key)
            deduped_log.append(entry)

    # Map internal ID → assigned units
    unit_map: dict[str, list[str]] = {}
    for entry in deduped_log:
        iid = entry.get("incident_id", "")
        uid = entry.get("unit_id", "")
        if iid and uid:
            unit_map.setdefault(iid, []).append(uid)

    # Merge new incidents into state
    new_feed_events: list[str] = []

    for inc in deduped_incidents:
        iid = inc.get("id", inc.get("master_incident_id", ""))
        if state.is_incident_seen(iid):
            continue
        state.mark_incident_seen(iid)

        display_id = state.next_incident_id()
        units = unit_map.get(iid, [])

        formatted = _format_incident(inc, display_id, units, now_str)
        state.add_incident(formatted, inc)

        icon = _get_icon(inc.get("resolved_type", inc.get("incident_type", "unknown")))
        severity = inc.get("severity", "MEDIUM").upper()
        severity_score = inc.get("severity_score", 0)
        calls_merged = inc.get("duplicate_count", 1)
        escalated = inc.get("escalation_reason") is not None

        feed_msg = (
            f"🚨 {icon} {formatted['type']} at {formatted['location']} "
            f"[{severity} • score {severity_score}/100]"
            + (f" — {calls_merged} calls merged" if calls_merged > 1 else "")
            + (" ⬆️ AUTO-ESCALATED" if escalated else "")
        )
        new_feed_events.append(feed_msg)

        # Emit WebSocket event
        if ws:
            await ws.emit_incident(formatted)

        for uid in units:
            entry_for_unit = next(
                (e for e in deduped_log
                 if e.get("unit_id") == uid and e.get("incident_id") == iid),
                None,
            )
            eta_str = (
                f" (ETA: {entry_for_unit['eta']:.0f} min)"
                if entry_for_unit and isinstance(entry_for_unit.get("eta"), (int, float))
                else ""
            )
            new_feed_events.append(f"🚑 {uid} dispatched → {formatted['location']}{eta_str}")

        # Format and store dispatch entries
        for entry in deduped_log:
            if entry.get("incident_id") == iid:
                formatted_dispatch = _format_dispatch_entry(entry, display_id)
                state.add_dispatch_entry(formatted_dispatch, entry)

                if ws:
                    await ws.emit_dispatch(formatted_dispatch)

        # Backend rerouting for CRITICAL incidents without units
        if severity == "CRITICAL" and not units:
            reroute = _attempt_backend_reroute(
                state, display_id, severity,
                inc.get("resources_needed", []),
            )
            if reroute:
                new_feed_events.append(
                    f"🔄 REROUTED {reroute['unit']} → {display_id} "
                    f"[pulled from LOW incident {reroute['rerouted_from']}]"
                )
                if ws:
                    await ws.emit_dispatch(reroute)

    # Resource strain check
    total_units = len(state.resources)
    dispatched_count = sum(1 for u in state.resources.values() if u.get("status") == "DISPATCHED")
    if total_units > 0 and dispatched_count / total_units > 0.6:
        new_feed_events.append(
            f"⚠️ Resource strain: {dispatched_count}/{total_units} units deployed"
        )

    # Update resources from pipeline
    pipeline_resources = result.get("resources", {})
    if pipeline_resources:
        state.update_resources(pipeline_resources)

    # Update city graph conditions
    try:
        state.city_graph.update_conditions(active_incidents=state.incidents)
    except (AttributeError, Exception):
        pass

    # Update reasoning
    raw_reasoning = result.get("agent_reasoning", {})
    n_incidents = len(state.incidents)
    n_dispatched = sum(
        1 for u in state.resources.values() if u.get("status") == "DISPATCHED"
    )
    context = (
        f"System state: {n_incidents} cumulative incident(s) | "
        f"{n_dispatched}/{len(state.resources)} units deployed"
    )
    state.update_reasoning(_humanize_reasoning(raw_reasoning, context))

    # Update alerts
    new_alerts = result.get("alerts", [])
    added_alerts = state.add_alerts(new_alerts)
    for alert in added_alerts:
        new_feed_events.append(f"⚠️ {alert}")
        if ws:
            await ws.emit_alert(alert)

    # Update live feed
    state.add_feed_events(new_feed_events)

    if ws and new_feed_events:
        await ws.emit_feed(new_feed_events)
        await ws.emit_reasoning(state.agent_reasoning)

    logger.info(
        "✅ Pipeline done — %d incident(s), %d dispatch(es)",
        len(state.incidents),
        len(state.dispatch_log),
    )

    return state.snapshot()
