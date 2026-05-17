"""Fusion Agent — Enhanced with multi-factor severity scoring.

Replaces simplistic call-count-based escalation with:
- Multi-factor severity scoring via severity_engine.py
- Zone-aware risk amplification
- Context-based incident type resolution
- Required resource package calculation
- Rich escalation explanations

The LLM merging logic is PRESERVED — only severity computation is upgraded.
"""

import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

from data.severity_engine import compute_severity_score
from data.zone_profiles import get_zone_profile, get_zone_risk_summary

load_dotenv()

def get_groq_client():
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))


def _compute_and_apply_severity(incidents: list[dict]) -> list[dict]:
    """Apply multi-factor severity scoring to each incident.

    Replaces the old call-count-based _escalate_severity().
    Uses the severity engine to compute a 0-100 score from:
    - incident type + context
    - casualty count
    - zone risk profile
    - corroboration confidence
    - hazmat/industrial indicators
    """
    for inc in incidents:
        incident_type = inc.get("incident_type", inc.get("type", "unknown"))
        location = inc.get("location", "downtown")
        injured = inc.get("injured_count", 0)
        dup_count = inc.get("duplicate_count", 1)
        confidence = inc.get("confidence_score", 50)
        summary = inc.get("summary", inc.get("caller_summary", ""))

        # Enrich summary with triage hazard flags for better type resolution
        enrichments = []
        if inc.get("has_chemical_hazard"):
            enrichments.append("chemical/hazmat involved")
        if inc.get("has_industrial_context"):
            enrichments.append("industrial/factory context")
        if inc.get("has_spread_risk"):
            enrichments.append("actively spreading")
        if inc.get("trapped_count", 0) > 0:
            enrichments.append(f"{inc['trapped_count']} people trapped")
            injured = max(injured, inc.get("trapped_count", 0))
        if inc.get("is_multi_casualty"):
            enrichments.append("multi-casualty event")
        if inc.get("time_critical_indicators"):
            enrichments.append(inc["time_critical_indicators"])

        if enrichments:
            summary = f"{summary}. Context: {', '.join(enrichments)}"

        # Compute severity score
        severity_result = compute_severity_score(
            incident_type=incident_type,
            location=location,
            injured_count=injured,
            duplicate_count=dup_count,
            confidence_score=confidence,
            summary=summary,
        )

        # Apply results to incident
        inc["severity_score"] = severity_result["severity_score"]
        inc["severity"] = severity_result["severity_label"]
        inc["resolved_type"] = severity_result["resolved_type"]
        inc["required_resources"] = severity_result["required_resources"]
        inc["severity_factors"] = severity_result["factors"]
        inc["severity_explanation"] = severity_result["explanation"]

        # Zone risk profile
        zone_profile = get_zone_profile(location)
        inc["zone_risk"] = {
            "zone": location,
            "population_density": zone_profile.get("population_density", 0.5),
            "hazard_level": zone_profile.get("hazard_level", 0.3),
            "infrastructure_importance": zone_profile.get("infrastructure_importance", 0.4),
            "chemical_sites": zone_profile.get("chemical_sites", False),
            "description": zone_profile.get("description", ""),
        }

        # Escalation tracking
        old_severity = inc.get("_original_severity")
        if old_severity and old_severity.upper() != inc["severity"]:
            inc["escalation_reason"] = (
                f"Severity upgraded from {old_severity.upper()} → {inc['severity']} "
                f"(score: {inc['severity_score']}/100). "
                f"{severity_result['explanation']}"
            )
        elif inc["severity_score"] >= 86:
            inc["escalation_reason"] = (
                f"CRITICAL severity (score: {inc['severity_score']}/100). "
                f"{severity_result['explanation']}"
            )
        else:
            inc.setdefault("escalation_reason", None)

    return incidents


def fusion_agent(state):
    """
    LangGraph node for Fusing triaged calls.
    Merges duplicates into master incidents, tracks confidence and call counts,
    and applies MULTI-FACTOR severity scoring (replaces old call-count escalation).
    """
    triage_outputs = state.get("triage_outputs", [])
    if not triage_outputs:
        return {"status": "Fusion Skipped (No triage outputs)"}

    groq_client = get_groq_client()

    system_prompt = """
    You are an emergency Fusion Agent. You receive a list of triaged emergency incidents as JSON.
    Some incidents are duplicates (same event, different callers or slightly different descriptions).

    Your task: group duplicates and merge into a single master incident per real-world event.

    Merging rules:
    1. Severity: Always take the HIGHEST severity (critical > high > medium > low).
    2. Resources: Take the UNION of all resources_needed.
    3. Injured count: Take the HIGHEST injured_count among duplicates.
    4. Trapped count: Take the HIGHEST trapped_count among duplicates.
    5. Location: Pick the most specific, clear zone name.
    6. Hazard flags: If ANY duplicate has has_chemical_hazard=true, set it true.
    7. Industrial flags: If ANY duplicate has has_industrial_context=true, set it true.
    8. Spread risk: If ANY duplicate has has_spread_risk=true, set it true.
    9. Multi-casualty: If ANY duplicate has is_multi_casualty=true, set it true.
    10. Time critical: Combine all time_critical_indicators.

    For each master incident output:
    - "duplicate_count": integer (total calls reporting this event)
    - "confidence_score": integer 0-100 (how confident they are the same incident)
      * 1 call = 40-60, 2 calls = 70-85, 3+ calls = 90-100
    - "summary": plain English combining all caller details

    Return ONLY a valid JSON object with a single key "incidents" mapping to a list.
    Each master incident:
    {
      "master_incident_id": "uuid string",
      "location": "string",
      "incident_type": "string",
      "severity": "string",
      "injured_count": integer,
      "trapped_count": integer,
      "resources_needed": ["string"],
      "duplicate_count": integer,
      "confidence_score": integer,
      "summary": "combined plain English summary",
      "has_chemical_hazard": boolean,
      "has_industrial_context": boolean,
      "has_spread_risk": boolean,
      "is_multi_casualty": boolean,
      "time_critical_indicators": "string"
    }
    """

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(triage_outputs, indent=2)}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result_json = response.choices[0].message.content
        fusion_data = json.loads(result_json)
        incidents = fusion_data.get("incidents", [])

        for inc in incidents:
            if "master_incident_id" not in inc:
                inc["master_incident_id"] = str(uuid.uuid4())
            inc["id"] = inc.get("master_incident_id", str(uuid.uuid4()))
            # Store original LLM severity for escalation tracking
            inc["_original_severity"] = inc.get("severity", "medium")

        # Apply multi-factor severity scoring (replaces old _escalate_severity)
        incidents = _compute_and_apply_severity(incidents)

        reasoning_parts = []
        for inc in incidents:
            count = inc.get("duplicate_count", 1)
            sev = inc.get("severity", "?").upper()
            score = inc.get("severity_score", 0)
            conf = inc.get("confidence_score", 0)
            resolved = inc.get("resolved_type", inc.get("incident_type", "?"))
            esc = inc.get("escalation_reason")
            req_res = inc.get("required_resources", {})
            res_str = ", ".join(f"{v}×{k}" for k, v in req_res.items())

            part = (
                f"{resolved.upper()} at {inc.get('location', '?')} — "
                f"{count} call(s) merged, severity={sev} (score={score}/100), "
                f"confidence={conf}%, resources=[{res_str}]."
            )
            if esc:
                part += f" [{esc}]"
            reasoning_parts.append(part)

        reasoning_summary = (
            f"Fusion Agent grouped {len(triage_outputs)} triaged call(s) into "
            f"{len(incidents)} unique master incident(s). "
            + " | ".join(reasoning_parts)
        )

    except Exception as e:
        incidents = []
        for t in triage_outputs:
            inc = dict(t)
            inc["master_incident_id"] = str(uuid.uuid4())
            inc["id"] = inc["master_incident_id"]
            inc["duplicate_count"] = 1
            inc["confidence_score"] = 50
            inc["summary"] = t.get("caller_summary", "")
            inc["_original_severity"] = t.get("severity", "medium")
            incidents.append(inc)

        incidents = _compute_and_apply_severity(incidents)
        reasoning_summary = (
            f"Fusion Agent fallback (LLM error: {str(e)}). "
            f"Passed through {len(incidents)} incident(s) without merging. "
            f"Multi-factor severity scoring still applied."
        )

    agent_reasoning = state.get("agent_reasoning", {})
    agent_reasoning["fusion"] = reasoning_summary

    # ── Normalize incident fields for downstream agents + dashboard ────
    for inc in incidents:
        if "id" not in inc:
            inc["id"] = inc.get("master_incident_id", str(uuid.uuid4()))
        if "type" not in inc and "incident_type" in inc:
            inc["type"] = inc["incident_type"]
        if "description" not in inc:
            inc["description"] = inc.get("summary", inc.get("caller_summary", "Emergency incident"))
        if "timestamp" not in inc:
            inc["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "status" not in inc:
            inc["status"] = "ACTIVE"
        if "calls_merged" not in inc:
            inc["calls_merged"] = inc.get("duplicate_count", 1)
        if "severity" in inc:
            inc["severity"] = inc["severity"].upper()
        # Clean up internal field
        inc.pop("_original_severity", None)

    incident = incidents[0] if incidents else {}

    # Build severity context for downstream agents
    severity_context = {}
    if incident:
        severity_context = {
            "primary_score": incident.get("severity_score", 0),
            "primary_label": incident.get("severity", "MEDIUM"),
            "primary_type": incident.get("resolved_type", "unknown"),
            "required_resources": incident.get("required_resources", {}),
            "zone_risk": incident.get("zone_risk", {}),
            "all_scores": [
                {
                    "id": inc.get("id"),
                    "score": inc.get("severity_score", 0),
                    "label": inc.get("severity", "MEDIUM"),
                    "type": inc.get("resolved_type", "unknown"),
                }
                for inc in incidents
            ],
        }

    # Zone risk profile for primary incident
    zone_risk_profile = incident.get("zone_risk", {})

    return {
        "incidents": incidents,
        "incident": incident,
        "agent_reasoning": agent_reasoning,
        "severity_context": severity_context,
        "zone_risk_profile": zone_risk_profile,
        "status": "Fusion Completed"
    }
