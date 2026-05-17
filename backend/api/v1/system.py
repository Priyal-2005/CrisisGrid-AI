"""System, state, and resource routes."""

from __future__ import annotations

from fastapi import APIRouter
from backend.core.state import get_state_manager

router = APIRouter(tags=["System"])


@router.get("/state")
async def get_full_state():
    """Get the complete system snapshot (incidents, resources, stats, etc)."""
    return get_state_manager().snapshot()


@router.get("/resources")
async def get_resources():
    """Get all resources and their current status/ETA."""
    state = get_state_manager().snapshot()
    return {"resources": state["resources"], "count": len(state["resources"])}


@router.get("/dispatch-log")
async def get_dispatch_log():
    """Get the full history of resource dispatches."""
    state = get_state_manager()
    return {"dispatch_log": list(reversed(state.dispatch_log))}


@router.get("/alerts")
async def get_alerts():
    """Get all system alerts (resource strain, mass casualty, etc)."""
    state = get_state_manager()
    return {"alerts": state.alerts}


@router.get("/reasoning")
async def get_reasoning():
    """Get the latest human-readable reasoning from all agents."""
    state = get_state_manager()
    return {"reasoning": state.agent_reasoning}


@router.get("/traffic")
async def get_traffic_report():
    """Get the current dynamic traffic condition report."""
    state = get_state_manager()
    try:
        report = state.city_graph.get_traffic_report()
        return report
    except AttributeError:
        return {"error": "Traffic reporting not supported by current graph implementation"}
