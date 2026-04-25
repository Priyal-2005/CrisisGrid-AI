import operator
from typing import Annotated, TypedDict, List, Dict, Any

class State(TypedDict):
    raw_calls: Annotated[List[str], operator.add]
    triage_outputs: Annotated[List[Dict[str, Any]], operator.add]
    incidents: Annotated[List[Dict[str, Any]], operator.add]
    dispatch_log: Annotated[List[Dict[str, Any]], operator.add]

    resources: Dict[str, Any]
    agent_reasoning: Dict[str, str]

    alerts: List[str]
    incident: Dict[str, Any]
    city_graph: Any
    status: str
