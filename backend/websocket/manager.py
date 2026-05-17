"""WebSocket connection manager for realtime event streaming.

Provides:
- Connection lifecycle management (connect/disconnect)
- Broadcast to all connected clients
- Per-client message sending
- Typed event emission (incident, dispatch, alert, feed, reasoning)
- Heartbeat keepalive
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from backend.core.logging import get_logger

logger = get_logger("websocket")
IST = timezone(timedelta(hours=5, minutes=30))


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts events."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.info("WS connected — %d active", self.connection_count)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket."""
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        logger.info("WS disconnected — %d active", self.connection_count)

    async def broadcast(self, event: dict) -> None:
        """Send an event to all connected clients.

        Silently removes broken connections.
        """
        if not self._connections:
            return

        payload = json.dumps(event, default=str)
        broken: list[WebSocket] = []

        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                broken.append(ws)

        if broken:
            async with self._lock:
                for ws in broken:
                    if ws in self._connections:
                        self._connections.remove(ws)
            logger.info("Cleaned %d broken WS connections", len(broken))

    async def send_personal(self, websocket: WebSocket, event: dict) -> None:
        """Send an event to a specific client."""
        try:
            await websocket.send_text(json.dumps(event, default=str))
        except Exception:
            await self.disconnect(websocket)

    # ── Typed event emitters ──

    async def emit_incident(self, incident: dict) -> None:
        """Broadcast a new/updated incident."""
        await self.broadcast({
            "type": "incident",
            "data": incident,
            "timestamp": datetime.now(IST).isoformat(),
        })

    async def emit_dispatch(self, dispatch_entry: dict) -> None:
        """Broadcast a dispatch event."""
        await self.broadcast({
            "type": "dispatch",
            "data": dispatch_entry,
            "timestamp": datetime.now(IST).isoformat(),
        })

    async def emit_alert(self, alert: str) -> None:
        """Broadcast a system alert."""
        await self.broadcast({
            "type": "alert",
            "data": {"message": alert},
            "timestamp": datetime.now(IST).isoformat(),
        })

    async def emit_feed(self, events: list[str]) -> None:
        """Broadcast live feed events."""
        await self.broadcast({
            "type": "feed",
            "data": events,
            "timestamp": datetime.now(IST).isoformat(),
        })

    async def emit_reasoning(self, reasoning: dict) -> None:
        """Broadcast agent reasoning update."""
        await self.broadcast({
            "type": "reasoning",
            "data": reasoning,
            "timestamp": datetime.now(IST).isoformat(),
        })

    async def emit_resource_update(self, resources: list[dict]) -> None:
        """Broadcast resource status changes."""
        await self.broadcast({
            "type": "resources",
            "data": resources,
            "timestamp": datetime.now(IST).isoformat(),
        })

    async def emit_state_snapshot(self, state: dict) -> None:
        """Broadcast a full state snapshot."""
        await self.broadcast({
            "type": "state_snapshot",
            "data": state,
            "timestamp": datetime.now(IST).isoformat(),
        })

    async def emit_system_event(self, event_name: str, data: Any = None) -> None:
        """Broadcast a generic system event."""
        await self.broadcast({
            "type": "system",
            "event": event_name,
            "data": data,
            "timestamp": datetime.now(IST).isoformat(),
        })


# ── Singleton ──

_ws_manager: ConnectionManager | None = None


def get_ws_manager() -> ConnectionManager:
    """Return the global ConnectionManager singleton."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = ConnectionManager()
    return _ws_manager
