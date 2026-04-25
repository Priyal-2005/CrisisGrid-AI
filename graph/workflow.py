"""LangGraph Workflow - Orchestrates all 4 CrisisGrid AI agents.

Pipeline: START → triage → fusion → dispatch → strategy → END

A conditional edge after dispatch skips strategy if no units were
available (escalation path).
"""

from langgraph.graph import StateGraph, END, START

from agents.triage_agent import triage_agent
from agents.fusion_agent import fusion_agent
from agents.dispatch_agent import dispatch_agent
from agents.strategy_agent import strategy_agent
from utils.state import State


# Conditional routing
def _should_run_strategy(state: State) -> str:
    """Decide whether to run the Strategy Agent after Dispatch.

    If the Dispatch Agent flagged "NO AVAILABLE UNITS" the strategy
    node is skipped — there is nothing to strategize over and the
    incident has already been marked for escalation.

    Args:
        state: Current pipeline state after the dispatch node.

    Returns:
        ``"strategy"`` to continue normally, or ``"end"`` to skip
        strategy and terminate the pipeline.
    """
    reasoning = state.get("agent_reasoning", {}).get("dispatch", "")
    if "NO AVAILABLE UNITS" in reasoning:
        return "end"
    return "strategy"


# Workflow builder
def create_workflow():
    """Build and compile the CrisisGrid AI LangGraph workflow.

    The graph is a simple linear chain:

        START → triage → fusion → dispatch →(cond)→ strategy → END
                                             └──────────────→ END

    Returns:
        A compiled LangGraph ``CompiledGraph`` ready for invocation.
    """
    workflow = StateGraph(State)

    # Add agent nodes
    workflow.add_node("triage", triage_agent)
    workflow.add_node("fusion", fusion_agent)
    workflow.add_node("dispatch", dispatch_agent)
    workflow.add_node("strategy", strategy_agent)

    # Linear edges
    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "fusion")
    workflow.add_edge("fusion", "dispatch")

    # Conditional edge: skip strategy when dispatch fails
    workflow.add_conditional_edges(
        "dispatch",
        _should_run_strategy,
        {
            "strategy": "strategy",
            "end": END,
        },
    )

    workflow.add_edge("strategy", END)

    return workflow.compile()


# Pipeline runner
def run_pipeline(
    transcript: str,
    resources: dict,
    city_graph: object,
) -> dict:
    """Run the full CrisisGrid AI pipeline on a single transcript.

    Initializes the shared state, invokes the compiled graph, and
    returns the final state dict containing all agent outputs.

    Args:
        transcript: Raw 112 emergency call text.
        resources:  Resource database — ``{unit_id: {type, status, location}}``.
        city_graph: NetworkX graph object with zones as nodes and
                    travel-time weighted edges.

    Returns:
        Final ``State`` dict after all agents have executed.
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

    final_state = compiled_graph.invoke(initial_state)
    return final_state
