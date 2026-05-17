"""Simulation service — runs mock scenarios through the pipeline.

Provides:
- Full mock simulation (all MOCK_CALLS)
- Structured test scenario (TEST_SCENARIO with step-by-step validation)
- Custom transcript sequence execution
- WebSocket progress broadcasting
"""

from __future__ import annotations

import asyncio

from data.mock_calls import MOCK_CALLS, TEST_SCENARIO
from data.resources import load_resources
from backend.core.state import StateManager
from backend.core.logging import get_logger
from backend.websocket.manager import ConnectionManager
from backend.services.pipeline_service import process_transcript

logger = get_logger("simulation")


async def run_simulation(
    state: StateManager,
    ws: ConnectionManager | None = None,
    calls: list[str] | None = None,
    delay: float = 2.0,
) -> dict:
    """Run all mock calls sequentially through the pipeline.

    Args:
        state: StateManager instance.
        ws: Optional WebSocket manager for realtime updates.
        calls: Custom transcripts (defaults to MOCK_CALLS).
        delay: Pause between calls in seconds.

    Returns:
        Final state snapshot with simulation metadata.
    """
    calls_to_run = calls or MOCK_CALLS
    total = len(calls_to_run)

    if ws:
        await ws.emit_system_event("simulation_start", {
            "total_calls": total,
            "delay": delay,
        })

    for i, transcript in enumerate(calls_to_run):
        logger.info("🔁 Simulation call %d/%d", i + 1, total)

        if ws:
            await ws.emit_system_event("simulation_progress", {
                "current": i + 1,
                "total": total,
                "transcript_preview": transcript[:80] + "...",
            })

        await process_transcript(transcript, state, ws)

        if i < total - 1:
            await asyncio.sleep(delay)

    logger.info("✅ Simulation complete — %d calls processed", total)

    if ws:
        await ws.emit_system_event("simulation_complete", {
            "calls_processed": total,
        })
        await ws.emit_state_snapshot(state.snapshot())

    return {
        "message": f"Simulation complete — {total} calls processed",
        "calls_processed": total,
        "state": state.snapshot(),
    }


async def run_scenario(
    state: StateManager,
    ws: ConnectionManager | None = None,
    delay: float = 1.5,
) -> dict:
    """Run the structured test scenario with step-by-step validation.

    Resets state first for a clean scenario run.

    Args:
        state: StateManager instance (will be reset).
        ws: Optional WebSocket manager.
        delay: Pause between scenario steps.

    Returns:
        Step-by-step results with validation data.
    """
    # Reset for clean scenario
    state.reset()

    if ws:
        await ws.emit_system_event("scenario_start", {
            "total_steps": len(TEST_SCENARIO),
        })

    steps = []

    for i, step in enumerate(TEST_SCENARIO):
        logger.info("📋 Scenario step %d: %s", i + 1, step["description"])

        if ws:
            await ws.emit_system_event("scenario_step", {
                "step": i + 1,
                "total": len(TEST_SCENARIO),
                "description": step["description"],
            })

        await process_transcript(step["call"], state, ws)

        step_result = {
            "step": i + 1,
            "description": step["description"],
            "expected_type": step["expected_type"],
            "expected_severity": step["expected_severity"],
            "incidents_so_far": len(state.incidents),
            "dispatches_so_far": len(state.dispatch_log),
            "alerts": list(state.alerts),
        }
        steps.append(step_result)

        if i < len(TEST_SCENARIO) - 1:
            await asyncio.sleep(delay)

    logger.info("✅ Scenario complete — %d steps", len(TEST_SCENARIO))

    if ws:
        await ws.emit_system_event("scenario_complete", {
            "steps_completed": len(TEST_SCENARIO),
        })
        await ws.emit_state_snapshot(state.snapshot())

    return {
        "message": "Test scenario complete",
        "steps": steps,
        "final_state": state.snapshot(),
    }
