"""Simulation and testing routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.schemas.models import SimulationRequest, ScenarioRequest
from backend.core.state import get_state_manager
from backend.websocket.manager import get_ws_manager
from backend.simulation.runner import run_simulation, run_scenario
from backend.core.config import get_settings

router = APIRouter(prefix="/simulation", tags=["Simulation"])
settings = get_settings()


@router.post("/run")
async def simulate(data: SimulationRequest):
    """Run sequential calls through the pipeline.

    Defaults to MOCK_CALLS. Demonstrates multi-incident accumulation,
    merging, and prioritization.
    """
    state = get_state_manager()
    ws = get_ws_manager()
    return await run_simulation(
        state, ws, data.calls, data.delay
    )


@router.post("/scenario")
async def scenario(data: ScenarioRequest):
    """Run the structured 6-step test scenario.

    Resets the state and verifies merging, escalation, prioritization,
    and re-routing step-by-step.
    """
    state = get_state_manager()
    ws = get_ws_manager()
    return await run_scenario(state, ws, data.delay)


@router.post("/reset")
async def reset_state():
    """Reset all state back to initial configuration.

    Useful for demo restarts. Restores resources to AVAILABLE.
    """
    state = get_state_manager()
    ws = get_ws_manager()
    result = state.reset()
    
    if ws:
        await ws.emit_system_event("system_reset")
        await ws.emit_state_snapshot(state.snapshot())
        
    return result
