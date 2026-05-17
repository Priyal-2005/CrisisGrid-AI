"""WebSocket route for realtime client connections."""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.websocket.manager import get_ws_manager
from backend.core.config import get_settings
from backend.core.state import get_state_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Realtime event stream for the dashboard.

    Sends initial state on connection, then streams incremental updates:
    - incidents
    - dispatches
    - alerts
    - feed events
    - resource updates
    """
    manager = get_ws_manager()
    state = get_state_manager()
    settings = get_settings()

    await manager.connect(websocket)
    
    # Send initial state snapshot immediately
    await manager.send_personal(websocket, {
        "type": "state_snapshot",
        "data": state.snapshot()
    })

    try:
        while True:
            # We don't expect client messages, but we need to receive to detect disconnects.
            # Use a timeout to occasionally send heartbeats.
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), 
                    timeout=settings.WS_HEARTBEAT_INTERVAL
                )
            except asyncio.TimeoutError:
                # Send heartbeat
                await manager.send_personal(websocket, {"type": "heartbeat"})
                continue
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
