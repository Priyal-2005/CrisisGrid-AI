"""Strategy Agent - Enhanced with infrastructure-aware reasoning.

Part of the CrisisGrid AI LangGraph multi-agent pipeline.
Runs AFTER the Dispatch Agent to review the entire system state,
identify resource conflicts, and make strategic decisions.

Enhancements over v1:
- Severity score-aware prioritization (not just tier)
- Zone risk and infrastructure criticality reasoning
- Cascade risk assessment
- Multi-incident resource balancing recommendations
- Enhanced rerouting: MEDIUM → CRITICAL (not just LOW → CRITICAL)
- Better explainability: WHY this decision, WHY NOT alternatives, WHAT tradeoff
"""

import os
from groq import Groq
from data.zone_profiles import get_zone_risk_summary


UTILIZATION_THRESHOLD = 0.75
LLM_MODEL = "llama-3.1-8b-instant"
SEVERITY_PRIORITY = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


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
                        "You have access to severity scores (0-100), zone risk profiles, and "
                        "infrastructure criticality data. "
                        "Be decisive and specific. Always structure your answer as:\n"
                        "SITUATION: [what is happening, severity scores and zone risks]\n"
                        "DECISION: [exact action taken, with unit IDs and incident IDs]\n"
                        "REASONING: [why this over alternatives, referencing severity scores]\n"
                        "TRADEOFF: [what risk is accepted and why it's acceptable]\n"
                        "CASCADE RISK: [any secondary/tertiary disaster risks and mitigation]"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as exc:
        return (
            f"SITUATION: LLM unavailable — rule-based fallback active.\n"
            f"DECISION: Prioritize by severity score; highest score gets resources first.\n"
            f"REASONING: Severity scores incorporate incident type, zone risk, casualties, "
            f"and cascade probability — more reliable than tier alone.\n"
            f"TRADEOFF: Lower-score incidents wait — acceptable given life-safety priority.\n"
            f"CASCADE RISK: Monitor industrial zones for secondary hazmat events.\n"
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
    unassigned: dict[str, list] = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
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
    """Find cases where a HIGH/CRITICAL incident lacks resources but a lower incident has them.

    Enhanced: now considers MEDIUM incidents as rerouting donors (not just LOW).
    Uses severity_score for smarter donor selection.
    """
    dispatched_ids = {entry.get("incident_id", "") for entry in dispatch_log}

    # Incidents needing resources (CRITICAL or HIGH, unassigned)
    needy_incidents = [
        inc for inc in incidents
        if inc.get("severity", "").upper() in ("CRITICAL", "HIGH")
        and inc.get("id", "") not in dispatched_ids
    ]
    if not needy_incidents:
        return []

    # Sort needy incidents by severity_score descending
    needy_incidents.sort(key=lambda x: -x.get("severity_score", 0))

    inc_data = {
        inc.get("id", ""): {
            "severity": inc.get("severity", "LOW").upper(),
            "score": inc.get("severity_score", 0),
        }
        for inc in incidents
    }

    opportunities = []
    for entry in dispatch_log:
        inc_id = entry.get("incident_id", "")
        unit_id = entry.get("unit_id", "")
        donor = inc_data.get(inc_id, {"severity": "LOW", "score": 0})

        # Can reroute from LOW or MEDIUM to CRITICAL/HIGH
        if donor["severity"] in ("CRITICAL", "HIGH"):
            continue
        if donor["score"] >= 66:
            continue  # Don't steal from high-scoring incidents

        unit = resources.get(unit_id, {})
        if unit.get("status") != "DISPATCHED":
            continue

        for needy in needy_incidents:
            opportunities.append({
                "critical_incident": needy.get("id"),
                "critical_score": needy.get("severity_score", 0),
                "critical_severity": needy.get("severity", "?"),
                "donor_incident": inc_id,
                "donor_severity": donor["severity"],
                "donor_score": donor["score"],
                "unit_to_reassign": unit_id,
                "unit_type": unit.get("type", "unknown"),
            })
            break  # One opportunity per donor unit

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

    # Consider both required_resources (new) and resources_needed (legacy)
    critical_demand: Counter = Counter()
    for inc in incidents:
        if inc.get("severity", "").upper() in ("CRITICAL", "HIGH"):
            # Prefer required_resources from severity engine
            req_resources = inc.get("required_resources", {})
            if req_resources:
                for rtype, count in req_resources.items():
                    critical_demand[rtype] += count
            else:
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


def _detect_cascade_risks(incidents: list[dict]) -> list[str]:
    """Identify potential cascading disaster scenarios from active incidents."""
    cascade_warnings = []

    for inc in incidents:
        if inc.get("status", "ACTIVE") != "ACTIVE":
            continue

        score = inc.get("severity_score", 0)
        resolved_type = inc.get("resolved_type", inc.get("incident_type", "unknown"))
        location = inc.get("location", "unknown")
        zone_risk = inc.get("zone_risk", {})

        # Chemical/industrial cascade risk
        if zone_risk.get("chemical_sites") and "fire" in resolved_type:
            cascade_warnings.append(
                f"CASCADE RISK: {resolved_type.upper()} at {location} (score {score}) — "
                f"CHEMICAL SITES in zone. Fire could trigger chemical explosion/toxic release. "
                f"Recommend hazmat pre-positioning and evacuation perimeter."
            )

        # High infrastructure cascade
        if zone_risk.get("infrastructure_importance", 0) >= 0.8:
            cascade_warnings.append(
                f"INFRASTRUCTURE RISK: {resolved_type.upper()} at {location} (score {score}) — "
                f"Critical infrastructure zone. Failure may cascade to transport/utility disruption. "
                f"Recommend alerting infrastructure operators."
            )

        # Multi-incident cascade (2+ incidents in nearby zones)
        # This is a simplified check — real systems use spatial clustering
        factors = inc.get("severity_factors", {})
        cascade_prob = factors.get("cascade_probability", 0)
        if cascade_prob >= 70:
            cascade_warnings.append(
                f"HIGH CASCADE PROBABILITY ({cascade_prob}%): {resolved_type.upper()} at {location}. "
                f"Secondary disaster likely — pre-position resources in adjacent zones."
            )

    return cascade_warnings


def _summarize_system_state(
    incidents: list[dict],
    resources: dict,
    utilization: float,
    dispatched: int,
    total: int,
) -> str:
    severity_counts: dict[str, int] = {}
    score_summary: list[str] = []
    for inc in incidents:
        sev = inc.get("severity", "UNKNOWN").upper()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        score = inc.get("severity_score", 0)
        iid = inc.get("id", "?")
        resolved = inc.get("resolved_type", inc.get("incident_type", "?"))
        location = inc.get("location", "?")
        score_summary.append(f"{iid}: {resolved} at {location} [score={score}, {sev}]")

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
        f"HIGH={severity_counts.get('HIGH',0)}, "
        f"MEDIUM={severity_counts.get('MEDIUM',0)}, LOW={severity_counts.get('LOW',0)}",
        f"Incident details:",
    ]
    for s in score_summary[:5]:
        lines.append(f"  - {s}")

    return "\n".join(lines)


def _build_llm_prompt(
    system_state_summary: str,
    conflict_description: str,
    rerouting_opportunities: list[dict],
    cascade_risks: list[str],
) -> str:
    reroute_section = ""
    if rerouting_opportunities:
        op = rerouting_opportunities[0]
        reroute_section = (
            f"\nRe-routing opportunity detected:\n"
            f"  {op['critical_severity']} incident {op['critical_incident']} "
            f"(score={op['critical_score']}) has no assigned units.\n"
            f"  {op['donor_severity']} incident {op['donor_incident']} "
            f"(score={op['donor_score']}) has {op['unit_type']} unit {op['unit_to_reassign']}.\n"
            f"  Score gap: {op['critical_score'] - op['donor_score']} points — "
            f"reassignment strongly justified.\n"
        )

    cascade_section = ""
    if cascade_risks:
        cascade_section = "\nCASCADE RISKS:\n" + "\n".join(f"  - {r}" for r in cascade_risks[:3])

    return (
        "You are an emergency response strategist.\n\n"
        f"SYSTEM STATE:\n{system_state_summary}\n\n"
        f"CONFLICTS DETECTED:\n{conflict_description}\n"
        f"{reroute_section}\n"
        f"{cascade_section}\n\n"
        "INSTRUCTIONS:\n"
        "- Use SEVERITY SCORES (0-100) to make decisions, not just tier labels\n"
        "- A score-96 industrial explosion outranks a score-72 residential fire\n"
        "- CRITICAL incidents ALWAYS take priority over HIGH, MEDIUM and LOW\n"
        "- If resources are limited: allocate by score, not by arrival order\n"
        "- If re-routing is needed: explicitly state unit IDs, from/to incidents\n"
        "- Address any CASCADE RISKS with pre-positioning recommendations\n"
        "- Format response EXACTLY as:\n"
        "  SITUATION: [1-2 sentences with severity scores]\n"
        "  DECISION: [specific action, unit IDs, incident IDs]\n"
        "  REASONING: [why this over alternatives, referencing scores]\n"
        "  TRADEOFF: [what risk is accepted]\n"
        "  CASCADE RISK: [secondary risks and mitigation]\n"
        "- Keep total response under 8 lines."
    )


def strategy_agent(state: dict) -> dict:
    """Analyze system state and make strategic prioritization decisions.

    Enhanced with:
    - Severity score-aware analysis (0-100 scoring)
    - Infrastructure and zone risk assessment
    - Cascade risk detection and mitigation
    - Multi-incident resource balancing
    - Rerouting from MEDIUM → CRITICAL/HIGH

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
    high_unassigned = unassigned_by_sev["HIGH"]
    medium_unassigned = unassigned_by_sev["MEDIUM"]

    if critical_unassigned:
        for inc in critical_unassigned:
            score = inc.get("severity_score", 0)
            iid = inc.get("id", "?")
            msg = (
                f"CRITICAL incident {iid} (score={score}/100) without dispatch — "
                f"immediate action required."
            )
            alerts.append(msg)
            conflicts_detected.append(msg)

    if high_unassigned:
        for inc in high_unassigned:
            score = inc.get("severity_score", 0)
            iid = inc.get("id", "?")
            conflicts_detected.append(
                f"HIGH incident {iid} (score={score}/100) pending dispatch."
            )

    if medium_unassigned:
        ids = [inc.get("id", "?") for inc in medium_unassigned]
        conflicts_detected.append(f"{len(medium_unassigned)} MEDIUM incident(s) pending: {ids}.")

    # 3. Resource shortages
    shortages = _detect_resource_shortage(resources, incidents)
    for s in shortages:
        msg = (
            f"RESOURCE SHORTAGE: {s['resource_type']} — "
            f"{s['available_count']} available vs {s['critical_demand']} HIGH/CRITICAL demand "
            f"(deficit: {s['deficit']} unit(s))."
        )
        alerts.append(msg)
        conflicts_detected.append(msg)

    # 4. Re-routing opportunities (enhanced: considers MEDIUM donors)
    rerouting_ops = _detect_rerouting_opportunities(incidents, resources, dispatch_log)
    for op in rerouting_ops:
        msg = (
            f"REROUTE RECOMMENDED: Pull {op['unit_to_reassign']} ({op['unit_type']}) "
            f"from {op['donor_severity']} incident {op['donor_incident']} (score={op['donor_score']}) "
            f"→ {op['critical_severity']} incident {op['critical_incident']} (score={op['critical_score']}). "
            f"Score gap: {op['critical_score'] - op['donor_score']} points."
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

    # 6. Dispatch reasoning context
    dispatch_reasoning = state.get("agent_reasoning", {}).get("dispatch", "")
    if "REROUTE" in dispatch_reasoning:
        conflicts_detected.append(
            f"Dynamic re-routing was executed this cycle: {dispatch_reasoning[:150]}..."
        )

    # 7. Cascade risk assessment (NEW)
    cascade_risks = _detect_cascade_risks(incidents)
    for risk in cascade_risks:
        alerts.append(risk)
        conflicts_detected.append(risk)

    # 8. Decision
    if not conflicts_detected:
        state["agent_reasoning"]["strategy"] = (
            "SITUATION: All incidents assigned, resources within normal bounds.\n"
            "DECISION: No strategic intervention required this cycle.\n"
            "REASONING: All CRITICAL/HIGH incidents have dispatched units; utilization below 75%.\n"
            "TRADEOFF: None — system operating optimally.\n"
            "CASCADE RISK: None detected — monitoring for escalation."
        )
        state["alerts"] = alerts
        return state

    # Real conflict → call LLM
    system_summary = _summarize_system_state(
        incidents, resources, utilization, dispatched, total
    )
    conflict_description = "\n".join(f"- {c}" for c in conflicts_detected)
    prompt = _build_llm_prompt(system_summary, conflict_description, rerouting_ops, cascade_risks)
    llm_response = call_llm_for_decision(prompt)

    state["agent_reasoning"]["strategy"] = llm_response
    state["alerts"] = alerts
    return state
