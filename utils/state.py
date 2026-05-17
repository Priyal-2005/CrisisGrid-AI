import operator
from typing import Annotated, TypedDict, List, Dict, Any

class State(TypedDict):
    # Lists that agents will append to during the workflow
    raw_calls: Annotated[List[str], operator.add]
    triage_outputs: Annotated[List[Dict[str, Any]], operator.add]
    incidents: Annotated[List[Dict[str, Any]], operator.add]
    dispatch_log: Annotated[List[Dict[str, Any]], operator.add]
    alerts: Annotated[List[str], operator.add]
    
    # Dictionaries overwritten or updated in place
    resources: Dict[str, Any]
    agent_reasoning: Dict[str, str]

    incident: Dict[str, Any]
    city_graph: Any
    status: str

    # --- Phase 1 enhancements ---
    # Severity scoring context passed between agents
    severity_context: Dict[str, Any]
    # Zone risk profile for the current primary incident
    zone_risk_profile: Dict[str, Any]