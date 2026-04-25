"""CrisisGrid AI - Shared LangGraph state schema."""

from typing import TypedDict, List, Dict


class CrisisState(TypedDict):
    """Shared state passed between all agents in the pipeline.

    Attributes:
        raw_calls:       Incoming emergency call transcripts.
        incidents:       Structured incident dicts produced by Triage/Fusion.
        resources:       All units and their current statuses.
        dispatch_log:    History of dispatch actions taken.
        agent_reasoning: Plain-English explanations keyed by agent name.
        alerts:          System-level warnings and recommendations.
        city_graph:      NetworkX graph object with zones and travel times.
    """
    raw_calls: List[str]
    incidents: List[Dict]
    resources: Dict
    dispatch_log: List[Dict]
    agent_reasoning: Dict[str, str]
    alerts: List[str]
    city_graph: object
