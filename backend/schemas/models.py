"""Pydantic schemas for CrisisGrid AI API.

Provides request/response validation for all endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


# ── Request schemas ──

class CallRequest(BaseModel):
    """Request body for processing a single emergency call."""
    transcript: str = Field(..., min_length=5, description="Raw 112 call transcript")


class SimulationRequest(BaseModel):
    """Request body for running a simulation."""
    delay: float = Field(2.0, ge=0.5, le=30.0, description="Delay between calls in seconds")
    calls: list[str] | None = Field(None, description="Custom call transcripts (uses defaults if None)")


class ScenarioRequest(BaseModel):
    """Request body for running the test scenario."""
    delay: float = Field(1.5, ge=0.5, le=30.0, description="Delay between scenario steps")


# ── Response schemas ──

class IncidentResponse(BaseModel):
    """Single incident data."""
    id: str
    internal_id: str = ""
    type: str
    resolved_type: str = ""
    location: str
    severity: str
    severity_score: int = 0
    status: str = "ACTIVE"
    units: list[str] = []
    time: str = ""
    timestamp: str = ""
    description: str = ""
    calls_merged: int = 1
    injured_count: int = 0
    trapped_count: int = 0
    resources_needed: list[str] = []
    required_resources: dict[str, int] = {}
    confidence_score: int = 50
    escalated: bool = False
    severity_explanation: str = ""
    zone_risk: dict[str, Any] = {}
    has_chemical_hazard: bool = False
    has_spread_risk: bool = False


class DispatchEntry(BaseModel):
    """Single dispatch log entry."""
    time: str = ""
    incident: str = ""
    incident_id: str = ""
    unit_id: str = ""
    unit: str = ""
    route: str = ""
    eta: str = ""
    severity: str = ""
    status: str = ""
    rerouted_from: str = ""


class ResourceResponse(BaseModel):
    """Single resource unit."""
    id: str
    type: str
    status: str
    location: str
    eta: int | None = None
    assigned_incident: str | None = None
    eta_display: str = ""


class StatsResponse(BaseModel):
    """System statistics."""
    total_incidents: int = 0
    total_dispatches: int = 0
    units_deployed: int = 0
    units_total: int = 0
    utilization: float = 0.0
    avg_severity_score: float = 0.0
    critical_count: int = 0
    high_count: int = 0


class SystemStateResponse(BaseModel):
    """Full system state snapshot."""
    incidents: list[dict] = []
    resources: list[dict] = []
    dispatch_log: list[dict] = []
    agent_reasoning: dict[str, str] = {}
    alerts: list[str] = []
    live_feed: list[str] = []
    stats: dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = ""
    incidents: int = 0
    resources: int = 0
    uptime_seconds: float = 0.0


class ProcessCallResponse(BaseModel):
    """Response from processing a call."""
    message: str = ""
    state: dict = {}


class SimulationResponse(BaseModel):
    """Response from a simulation run."""
    message: str = ""
    calls_processed: int = 0
    state: dict = {}


class ScenarioResponse(BaseModel):
    """Response from a scenario run."""
    message: str = ""
    steps: list[dict] = []
    final_state: dict = {}


class ResetResponse(BaseModel):
    """Response from state reset."""
    message: str = ""
    resources: int = 0


# ── WebSocket schemas ──

class WSEvent(BaseModel):
    """WebSocket event payload."""
    type: str
    data: Any = None
    timestamp: str = ""
