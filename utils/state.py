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
