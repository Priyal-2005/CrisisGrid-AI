"""Incident and dispatch call processing routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.schemas.models import CallRequest
from backend.core.state import get_state_manager
from backend.websocket.manager import get_ws_manager
from backend.services.pipeline_service import process_transcript
from backend.core.logging import get_logger

logger = get_logger("api.incidents")
router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("")
async def list_incidents():
    """Get all active incidents ordered by severity score."""
    state = get_state_manager()
    incidents = sorted(
        state.incidents,
        key=lambda x: -x.get("severity_score", 0),
    )
    return {"incidents": incidents, "count": len(incidents)}


@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    """Get a single incident by display ID (e.g. INC-001)."""
    state = get_state_manager()
    inc = next(
        (i for i in state.incidents if i["id"] == incident_id),
        None,
    )
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return inc


@router.post("/process-call")
async def process_call(data: CallRequest):
    """Process a single emergency call through the full 4-agent pipeline.

    This is the primary API endpoint. Accepts a raw 112 transcript,
    runs it through Triage → Fusion → Dispatch → Strategy, and
    returns the updated system state.
    """
    state = get_state_manager()
    ws = get_ws_manager()

    logger.info("📞 Call: %s...", data.transcript[:80])
    try:
        result = await process_transcript(data.transcript, state, ws)
        return {"message": "Call processed successfully", "state": result}
    except Exception as exc:
        logger.error("❌ Pipeline error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
