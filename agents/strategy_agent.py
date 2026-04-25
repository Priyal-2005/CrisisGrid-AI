"""Strategy Agent - Makes high-level trade-off decisions.

Part of the CrisisGrid AI LangGraph multi-agent pipeline.
Runs AFTER the Dispatch Agent to review the entire system state,
identify resource conflicts, and make strategic decisions with
plain-English explanations for full transparency.
"""

import os
from groq import Groq


# Constants
UTILIZATION_THRESHOLD = 0.75  # 75 % — triggers a standby alert
LLM_MODEL = "llama-3.1-8b-instant"



# LLM helper
def call_llm_for_decision(prompt: str) -> str:
    """Call the Groq API for strategic reasoning.

    Args:
        prompt: Fully-formed prompt describing the system state and
                the conflict that requires a decision.

    Returns:
        The LLM's response text.  Falls back to a generic message
        if the API call fails for any reason.
    """
    try:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an emergency response strategist for a "
                        "city-wide crisis management system. Be concise, "
                        "practical, and decisive."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        return (
            f"LLM unavailable ({exc}). Falling back to rule-based "
            "strategy: prioritize highest-severity incident and "
            "request mutual aid if resources are exhausted."
        )


# Internal analysis helpers
def _calculate_utilization(resources: dict) -> tuple[float, int, int]:
    """Compute system-wide resource utilization.

    Args:
        resources: ``state.resources`` dict.

    Returns:
        A tuple of (utilization_ratio, dispatched_count, total_count).
    """
    total = len(resources)
    if total == 0:
        return 0.0, 0, 0
    dispatched = sum(
        1 for u in resources.values() if u.get("status") == "DISPATCHED"
    )
    return dispatched / total, dispatched, total


def _get_unassigned_critical_incidents(
    incidents: list[dict],
    dispatch_log: list[dict],
) -> list[dict]:
    """Find CRITICAL incidents that have no dispatch entry.

    Args:
        incidents:    ``state.incidents`` list.
        dispatch_log: ``state.dispatch_log`` list.

    Returns:
        List of incident dicts with severity ``"CRITICAL"`` and no
        matching entry in the dispatch log.
    """
    dispatched_ids: set[str] = {
        entry["incident_id"] for entry in dispatch_log
    }
    return [
        inc for inc in incidents
        if inc.get("severity", "").upper() == "CRITICAL"
        and inc.get("id") not in dispatched_ids
    ]


def _detect_resource_shortage(
    resources: dict,
    incidents: list[dict],
) -> list[dict]:
    """Identify resource types with only one AVAILABLE unit remaining
    while multiple CRITICAL incidents still need that type.

    Args:
        resources: ``state.resources`` dict.
        incidents: ``state.incidents`` list.

    Returns:
        List of dicts describing each shortage:
        ``{resource_type, available_count, critical_demand}``.
    """
    from collections import Counter

    # Count available units per type
    available_by_type: dict[str, int] = Counter()
    for unit in resources.values():
        if unit.get("status") == "AVAILABLE":
            available_by_type[unit["type"]] += 1

    # Count critical-incident demand per resource type
    # (uses the same mapping as dispatch_agent)
    TYPE_MAP = {
        "Fire": "fire_truck",
        "Medical": "ambulance",
        "Police": "police",
        "Ambulance": "ambulance",
        "Fire Truck": "fire_truck",
        "fire": "fire_truck",
        "medical": "ambulance",
        "police": "police",
        "ambulance": "ambulance",
        "fire_truck": "fire_truck",
    }

    critical_demand: Counter = Counter()
    for inc in incidents:
        if inc.get("severity", "").upper() == "CRITICAL":
            for need in inc.get("resources_needed", []):
                unit_type = TYPE_MAP.get(need)
                if unit_type:
                    critical_demand[unit_type] += 1

    shortages: list[dict] = []
    for rtype, demand in critical_demand.items():
        avail = available_by_type.get(rtype, 0)
        if avail < demand:
            shortages.append({
                "resource_type": rtype,
                "available_count": avail,
                "critical_demand": demand,
            })
    return shortages


def _build_llm_prompt(
    system_state_summary: str,
    conflict_description: str,
) -> str:
    """Construct the structured prompt sent to the LLM.

    Args:
        system_state_summary:  Plain-text overview of resources, incidents,
                               and utilization.
        conflict_description:  Description of the conflict or ambiguity
                               that needs a decision.

    Returns:
        A formatted prompt string.
    """
    return (
        "You are an emergency response strategist.\n\n"
        f"System State:\n{system_state_summary}\n\n"
        f"Problem:\n{conflict_description}\n\n"
        "Instructions:\n"
        "- Choose the best action under resource constraints\n"
        "- Be concise and practical\n"
        "- Output 3 parts:\n"
        "  1. Situation summary\n"
        "  2. Decision\n"
        "  3. Reasoning\n\n"
        "Keep response under 5 lines."
    )


def _summarize_system_state(
    incidents: list[dict],
    resources: dict,
    utilization: float,
    dispatched: int,
    total: int,
) -> str:
    """Build a concise system-state summary for the LLM prompt.

    Args:
        incidents:   Active incident list.
        resources:   Resource dict.
        utilization: Current utilization ratio.
        dispatched:  Count of dispatched units.
        total:       Total unit count.

    Returns:
        Multi-line plain-text summary.
    """
    severity_counts: dict[str, int] = {}
    for inc in incidents:
        sev = inc.get("severity", "UNKNOWN").upper()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    available_by_type: dict[str, int] = {}
    for unit in resources.values():
        if unit.get("status") == "AVAILABLE":
            utype = unit.get("type", "unknown")
            available_by_type[utype] = available_by_type.get(utype, 0) + 1

    lines = [
        f"Total units: {total}, Dispatched: {dispatched}, "
        f"Utilization: {utilization:.0%}",
        f"Active incidents: {len(incidents)} — {severity_counts}",
        f"Available units by type: {available_by_type}",
    ]
    return "\n".join(lines)


# Main agent entry point
def strategy_agent(state: dict) -> dict:
    """Analyze system state and make strategic decisions.

    Runs deterministic rule-based checks first (utilization thresholds,
    resource shortages, unassigned criticals).  Only invokes the LLM
    when a genuine conflict or ambiguity is detected.

    Args:
        state: LangGraph state object containing at minimum:
            - ``incidents``       – list of all active incident dicts.
            - ``resources``       – dict of all units keyed by unit ID.
            - ``dispatch_log``    – list of dispatch-log entries.
            - ``agent_reasoning`` – dict of reasoning from prior agents.

    Returns:
        The mutated *state* dict with:
            - ``agent_reasoning["strategy"]`` – plain-English decision.
            - ``alerts`` – list of system warning strings.
    """
    # Extract state fields
    incidents: list[dict] = state.get("incidents", [])
    resources: dict = state.get("resources", {})
    dispatch_log: list[dict] = state.get("dispatch_log", [])

    # Ensure mutable containers exist
    if "agent_reasoning" not in state:
        state["agent_reasoning"] = {}
    if "alerts" not in state:
        state["alerts"] = []

    alerts: list[str] = state["alerts"]
    conflicts_detected: list[str] = []

    # 1. System utilization
    utilization, dispatched, total = _calculate_utilization(resources)

    if utilization > UTILIZATION_THRESHOLD:
        alerts.append(
            "WARNING: High resource utilization "
            f"({utilization:.0%}). Recommend standby alert."
        )
        conflicts_detected.append(
            f"System overload — {utilization:.0%} of units dispatched "
            f"({dispatched}/{total})."
        )

    # 2. Unassigned critical incidents
    unassigned_criticals = _get_unassigned_critical_incidents(
        incidents, dispatch_log,
    )
    if unassigned_criticals:
        ids = [inc["id"] for inc in unassigned_criticals]
        alerts.append(
            f"CRITICAL incidents without dispatch: {', '.join(ids)}"
        )
        conflicts_detected.append(
            f"{len(unassigned_criticals)} CRITICAL incident(s) have no "
            f"dispatched resource: {ids}."
        )

    # 3. Resource shortages
    shortages = _detect_resource_shortage(resources, incidents)
    if shortages:
        for s in shortages:
            msg = (
                f"Resource shortage: {s['resource_type']} — "
                f"{s['available_count']} available vs "
                f"{s['critical_demand']} critical demand."
            )
            alerts.append(msg)
            conflicts_detected.append(msg)

    #  4. No available units at all
    any_available = any(
        u.get("status") == "AVAILABLE" for u in resources.values()
    )
    if not any_available and total > 0:
        alerts.append(
            "ALL UNITS DISPATCHED. Recommend mutual aid request "
            "from neighboring district."
        )
        conflicts_detected.append(
            "Zero available units across all types. Mutual aid required."
        )

    # 5. Decision
    if not conflicts_detected:
        # No issues — all dispatches are optimal.
        state["agent_reasoning"]["strategy"] = (
            "All dispatches optimal. No strategic intervention needed."
        )
        state["alerts"] = alerts
        return state

    # A real conflict exists — call the LLM for a nuanced decision.
    system_summary = _summarize_system_state(
        incidents, resources, utilization, dispatched, total,
    )
    conflict_description = "\n".join(
        f"- {c}" for c in conflicts_detected
    )

    prompt = _build_llm_prompt(system_summary, conflict_description)
    llm_response = call_llm_for_decision(prompt)

    state["agent_reasoning"]["strategy"] = llm_response
    state["alerts"] = alerts
    return state
