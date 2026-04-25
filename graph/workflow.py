"""LangGraph Workflow - Orchestrates all 4 CrisisGrid AI agents.

Pipeline: START → triage → fusion → dispatch → strategy → END

Strategy ALWAYS runs — even when dispatch fails — because escalation
decisions require strategic reasoning.
"""

from langgraph.graph import StateGraph, END, START

from agents.triage_agent import triage_agent
from agents.fusion_agent import fusion_agent
from agents.dispatch_agent import dispatch_agent
from agents.strategy_agent import strategy_agent
from utils.state import State


def create_workflow():
    """Build and compile the CrisisGrid AI LangGraph workflow.

    Graph:
        START → triage → fusion → dispatch → strategy → END

    Strategy always runs so escalation decisions are always generated,
    even when no units are available.
    """
    workflow = StateGraph(State)

    workflow.add_node("triage", triage_agent)
    workflow.add_node("fusion", fusion_agent)
    workflow.add_node("dispatch", dispatch_agent)
    workflow.add_node("strategy", strategy_agent)

    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "fusion")
    workflow.add_edge("fusion", "dispatch")
    workflow.add_edge("dispatch", "strategy")
    workflow.add_edge("strategy", END)

    return workflow.compile()


def run_pipeline(
    transcript: str,
    resources: dict,
    city_graph: object,
) -> dict:
    """Run the full pipeline from scratch on a single transcript.

    Creates a fresh state — use for standalone invocation or testing.
    """
    compiled_graph = create_workflow()

    initial_state: State = {
        "raw_calls": [transcript],
        "triage_outputs": [],
        "incidents": [],
        "dispatch_log": [],
        "resources": resources,
        "agent_reasoning": {},
        "alerts": [],
        "incident": {},
        "city_graph": city_graph,
        "status": "initialized"
    }

    return compiled_graph.invoke(initial_state)


def run_pipeline_stateful(state: dict, transcript: str) -> dict:
    """Run pipeline on a persistent state, processing one new call.

    Carries forward resources and agent_reasoning from existing state.
    Incidents and dispatch_log start fresh per-call — accumulation is
    handled by the backend layer (colab_backend.py) which deduplicates
    and merges results into current_state.

    Args:
        state: Persistent state dict from the backend.
        transcript: New raw 112 call transcript.

    Returns:
        Final State dict with this call's pipeline results.
    """
    compiled_graph = create_workflow()

    call_state: State = {
        "raw_calls": [transcript],
        "triage_outputs": [],
        "incidents": [],
        "dispatch_log": [],
        "resources": state.get("resources", {}),
        "agent_reasoning": state.get("agent_reasoning", {}),
        "alerts": [],
        "incident": {},
        "city_graph": state.get("city_graph"),
        "status": "processing"
    }

    return compiled_graph.invoke(call_state)
