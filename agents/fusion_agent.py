import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def get_groq_client():
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Severity escalation threshold: 3+ reports of the same incident → CRITICAL
ESCALATION_CALL_THRESHOLD = 3


def _escalate_severity(incidents: list[dict]) -> list[dict]:
    """
    Post-process fusion results:
    - If duplicate_count >= 3 and severity is not CRITICAL, escalate to CRITICAL.
    - Record the escalation reason.
    """
    for inc in incidents:
        count = inc.get("duplicate_count", 1)
        sev = inc.get("severity", "LOW").upper()
        if count >= ESCALATION_CALL_THRESHOLD and sev != "CRITICAL":
            inc["severity"] = "CRITICAL"
            inc["escalation_reason"] = (
                f"Auto-escalated to CRITICAL: {count} independent callers reported this incident. "
                f"Multiple corroborating reports indicate confirmed large-scale emergency."
            )
        elif count >= 2 and sev == "LOW":
            inc["severity"] = "MEDIUM"
            inc["escalation_reason"] = (
                f"Upgraded LOW → MEDIUM: {count} callers confirmed the incident."
            )
        else:
            inc.setdefault("escalation_reason", None)
    return incidents


def fusion_agent(state):
    """
    LangGraph node for Fusing triaged calls.
    Merges duplicates into master incidents, tracks confidence and call counts,
    and applies severity escalation rules.
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
    1. Severity: Always take the HIGHEST severity (critical > medium > low).
    2. Resources: Take the UNION of all resources_needed.
    3. Injured count: Take the HIGHEST injured_count among duplicates.
    4. Location: Pick the most specific, clear zone name.

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
      "resources_needed": ["string"],
      "duplicate_count": integer,
      "confidence_score": integer,
      "summary": "combined plain English summary"
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

        # Apply escalation rules
        incidents = _escalate_severity(incidents)

        reasoning_parts = []
        for inc in incidents:
            count = inc.get("duplicate_count", 1)
            sev = inc.get("severity", "?").upper()
            conf = inc.get("confidence_score", 0)
            esc = inc.get("escalation_reason")
            part = (
                f"{inc.get('incident_type','?').upper()} at {inc.get('location','?')} — "
                f"{count} call(s) merged, severity={sev}, confidence={conf}%."
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
            incidents.append(inc)

        incidents = _escalate_severity(incidents)
        reasoning_summary = (
            f"Fusion Agent fallback (LLM error: {str(e)}). "
            f"Passed through {len(incidents)} incident(s) without merging. "
            f"Escalation rules still applied."
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

    incident = incidents[0] if incidents else {}

    return {
        "incidents": incidents,
        "incident": incident,
        "agent_reasoning": agent_reasoning,
        "status": "Fusion Completed"
    }
