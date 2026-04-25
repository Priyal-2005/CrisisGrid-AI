"""Strategy Agent - Makes high-level trade-off decisions.

Part of the CrisisGrid AI LangGraph multi-agent pipeline.
Runs AFTER the Dispatch Agent to review the entire system state,
identify resource conflicts, and make strategic decisions with
explicit: WHY this decision, WHY NOT alternatives, WHAT tradeoff.
"""

import os
from groq import Groq


UTILIZATION_THRESHOLD = 0.75
LLM_MODEL = "llama-3.1-8b-instant"
SEVERITY_PRIORITY = {"CRITICAL": 0, "MEDIUM": 1, "LOW": 2}


def call_llm_for_decision(prompt: str) -> str:
    try:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an emergency response strategist for a city-wide crisis system. "
                        "Be decisive and specific. Always structure your answer as:\n"
                        "SITUATION: [what is happening]\n"
                        "DECISION: [exact action taken]\n"
                        "REASONING: [why this over alternatives]\n"
                        "TRADEOFF: [what risk is accepted and why it's acceptable]"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as exc:
        return (
            f"SITUATION: LLM unavailable — rule-based fallback active.\n"
            f"DECISION: Prioritize CRITICAL incidents; hold MEDIUM in queue; delay LOW.\n"
            f"REASONING: CRITICAL incidents risk loss of life; cannot delay.\n"
            f"TRADEOFF: LOW-priority incidents wait — acceptable given life-safety priority.\n"
            f"(LLM error: {exc})"
        )


def _calculate_utilization(resources: dict) -> tuple[float, int, int]:
    total = len(resources)
    if total == 0:
        return 0.0, 0, 0
    dispatched = sum(1 for u in resources.values() if u.get("status") == "DISPATCHED")
    return dispatched / total, dispatched, total


def _get_unassigned_incidents_by_priority(
    incidents: list[dict],
    dispatch_log: list[dict],
) -> dict[str, list[dict]]:
    """Categorize all unassigned incidents by severity."""
    dispatched_ids = {entry.get("incident_id", "") for entry in dispatch_log}
    unassigned: dict[str, list] = {"CRITICAL": [], "MEDIUM": [], "LOW": []}
    for inc in incidents:
        iid = inc.get("id", "")
        if iid not in dispatched_ids:
            sev = inc.get("severity", "LOW").upper()
            bucket = unassigned.get(sev, unassigned["LOW"])
            bucket.append(inc)
    return unassigned


def _detect_rerouting_opportunities(
    incidents: list[dict],
    resources: dict,
    dispatch_log: list[dict],
) -> list[dict]:
    """Find cases where a CRITICAL incident lacks resources but a LOW incident has them."""
    dispatched_ids = {entry.get("incident_id", "") for entry in dispatch_log}

    critical_unassigned = [
        inc for inc in incidents
        if inc.get("severity", "").upper() == "CRITICAL"
        and inc.get("id", "") not in dispatched_ids
    ]
    if not critical_unassigned:
        return []

    inc_severity = {inc.get("id", ""): inc.get("severity", "LOW").upper() for inc in incidents}

    opportunities = []
    for entry in dispatch_log:
        inc_id = entry.get("incident_id", "")
        unit_id = entry.get("unit_id", "")
        if inc_severity.get(inc_id, "CRITICAL") == "LOW":
            unit = resources.get(unit_id, {})
            if unit.get("status") == "DISPATCHED":
                opportunities.append({
                    "critical_incident": critical_unassigned[0].get("id"),
                    "low_incident": inc_id,
                    "unit_to_reassign": unit_id,
                    "unit_type": unit.get("type", "unknown"),
                })
    return opportunities


def _detect_resource_shortage(resources: dict, incidents: list[dict]) -> list[dict]:
    from collections import Counter
    TYPE_MAP = {
        "fire": "fire_truck", "Fire": "fire_truck", "fire_truck": "fire_truck",
        "Fire Truck": "fire_truck", "ambulance": "ambulance", "Ambulance": "ambulance",
        "Medical": "ambulance", "medical": "ambulance",
        "police": "police", "Police": "police",
    }
    available_by_type: Counter = Counter()
    for unit in resources.values():
        if unit.get("status") == "AVAILABLE":
            available_by_type[unit["type"]] += 1

    critical_demand: Counter = Counter()
    for inc in incidents:
        if inc.get("severity", "").upper() == "CRITICAL":
            for need in inc.get("resources_needed", []):
                unit_type = TYPE_MAP.get(need)
                if unit_type:
                    critical_demand[unit_type] += 1

    shortages = []
    for rtype, demand in critical_demand.items():
        avail = available_by_type.get(rtype, 0)
        if avail < demand:
            shortages.append({
                "resource_type": rtype,
                "available_count": avail,
                "critical_demand": demand,
                "deficit": demand - avail,
            })
    return shortages


def _summarize_system_state(
    incidents: list[dict],
    resources: dict,
    utilization: float,
    dispatched: int,
    total: int,
) -> str:
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
        f"Total units: {total} | Dispatched: {dispatched} | Utilization: {utilization:.0%}",
        f"Active incidents: {len(incidents)} breakdown: {severity_counts}",
        f"Available units by type: {available_by_type}",
        f"Priority queue: CRITICAL={severity_counts.get('CRITICAL',0)}, "
        f"MEDIUM={severity_counts.get('MEDIUM',0)}, LOW={severity_counts.get('LOW',0)}",
    ]
    return "\n".join(lines)


def _build_llm_prompt(
    system_state_summary: str,
    conflict_description: str,
    rerouting_opportunities: list[dict],
) -> str:
    reroute_section = ""
    if rerouting_opportunities:
        op = rerouting_opportunities[0]
        reroute_section = (
            f"\nRe-routing opportunity detected:\n"
            f"  CRITICAL incident {op['critical_incident']} has no assigned units.\n"
            f"  LOW incident {op['low_incident']} has {op['unit_type']} unit {op['unit_to_reassign']} dispatched.\n"
            f"  Recommend reassigning {op['unit_to_reassign']} from LOW to CRITICAL immediately.\n"
        )

    return (
        "You are an emergency response strategist.\n\n"
        f"SYSTEM STATE:\n{system_state_summary}\n\n"
        f"CONFLICTS DETECTED:\n{conflict_description}\n"
        f"{reroute_section}\n"
        "INSTRUCTIONS:\n"
        "- CRITICAL incidents ALWAYS take priority over MEDIUM and LOW\n"
        "- If resources are limited: allocate to CRITICAL first, delay MEDIUM, queue LOW\n"
        "- If re-routing is needed: explicitly state which unit to pull and from where\n"
        "- Format your response EXACTLY as:\n"
        "  SITUATION: [1 sentence]\n"
        "  DECISION: [specific action, unit IDs if possible]\n"
        "  REASONING: [why this over alternatives]\n"
        "  TRADEOFF: [what risk is accepted]\n"
        "- Keep total response under 6 lines."
    )


def strategy_agent(state: dict) -> dict:
    """Analyze system state and make strategic prioritization decisions.

    Always runs — even when dispatch failed (escalation needs strategy most).
    Uses rule-based checks first, LLM only when real conflicts exist.
    """
    incidents: list[dict] = state.get("incidents", [])
    resources: dict = state.get("resources", {})
    dispatch_log: list[dict] = state.get("dispatch_log", [])

    state.setdefault("agent_reasoning", {})
    state.setdefault("alerts", [])

    alerts: list[str] = state["alerts"]
    conflicts_detected: list[str] = []

    # 1. System utilization check
    utilization, dispatched, total = _calculate_utilization(resources)
    if utilization >= UTILIZATION_THRESHOLD:
        msg = (
            f"HIGH UTILIZATION ALERT: {utilization:.0%} of units deployed "
            f"({dispatched}/{total}). System approaching capacity."
        )
        alerts.append(msg)
        conflicts_detected.append(msg)

    # 2. Categorize unassigned incidents by priority
    unassigned_by_sev = _get_unassigned_incidents_by_priority(incidents, dispatch_log)
    critical_unassigned = unassigned_by_sev["CRITICAL"]
    medium_unassigned = unassigned_by_sev["MEDIUM"]

    if critical_unassigned:
        ids = [inc.get("id", "?") for inc in critical_unassigned]
        msg = f"CRITICAL incidents without dispatch: {', '.join(ids)} — immediate action required."
        alerts.append(msg)
        conflicts_detected.append(msg)

    if medium_unassigned:
        ids = [inc.get("id", "?") for inc in medium_unassigned]
        conflicts_detected.append(f"{len(medium_unassigned)} MEDIUM incident(s) pending dispatch: {ids}.")

    # 3. Resource shortages
    shortages = _detect_resource_shortage(resources, incidents)
    for s in shortages:
        msg = (
            f"RESOURCE SHORTAGE: {s['resource_type']} — "
            f"{s['available_count']} available vs {s['critical_demand']} CRITICAL demand "
            f"(deficit: {s['deficit']} unit(s))."
        )
        alerts.append(msg)
        conflicts_detected.append(msg)

    # 4. Re-routing opportunities
    rerouting_ops = _detect_rerouting_opportunities(incidents, resources, dispatch_log)
    for op in rerouting_ops:
        msg = (
            f"REROUTE RECOMMENDED: Pull {op['unit_to_reassign']} ({op['unit_type']}) "
            f"from LOW incident {op['low_incident']} → CRITICAL incident {op['critical_incident']}."
        )
        alerts.append(msg)
        conflicts_detected.append(msg)

    # 5. All units exhausted
    any_available = any(u.get("status") == "AVAILABLE" for u in resources.values())
    if not any_available and total > 0:
        msg = (
            "ALL UNITS DISPATCHED — ESCALATING. "
            "Zero available units across all types. "
            "Immediate mutual aid request required from neighboring district."
        )
        alerts.append(msg)
        conflicts_detected.append(msg)

    # 6. Dispatch reasoning context (what the dispatch agent just decided)
    dispatch_reasoning = state.get("agent_reasoning", {}).get("dispatch", "")
    if "REROUTE" in dispatch_reasoning:
        conflicts_detected.append(
            f"Dynamic re-routing was executed this cycle: {dispatch_reasoning[:120]}..."
        )

    # 7. Decision
    if not conflicts_detected:
        state["agent_reasoning"]["strategy"] = (
            "SITUATION: All incidents assigned, resources within normal bounds.\n"
            "DECISION: No strategic intervention required this cycle.\n"
            "REASONING: All CRITICAL incidents have dispatched units; utilization below 75%.\n"
            "TRADEOFF: None — system operating optimally."
        )
        state["alerts"] = alerts
        return state

    # Real conflict → call LLM
    system_summary = _summarize_system_state(
        incidents, resources, utilization, dispatched, total
    )
    conflict_description = "\n".join(f"- {c}" for c in conflicts_detected)
    prompt = _build_llm_prompt(system_summary, conflict_description, rerouting_ops)
    llm_response = call_llm_for_decision(prompt)

    state["agent_reasoning"]["strategy"] = llm_response
    state["alerts"] = alerts
    return state
