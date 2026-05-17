"""Triage Agent — Enhanced with multi-factor severity intelligence.

Extracts richer structured data from raw 112 calls including:
- Hazmat indicators
- Industrial/chemical context
- Trapped persons count
- Spread risk indicators
- Infrastructure context

The severity_score is computed AFTER triage by the severity engine,
but triage provides the raw signals that feed into the score.
"""

import os
import json
import uuid
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def get_groq_client():
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))

def triage_agent(state):
    """
    LangGraph node function for Triaging raw calls.
    Takes raw Hinglish calls and extracts structured JSON data
    with enhanced fields for multi-factor severity scoring.
    """
    raw_calls = state.get("raw_calls", [])
    if not raw_calls:
        return {"status": "No calls to triage"}
        
    groq_client = get_groq_client()
    triage_outputs = []
    reasoning_notes = []
    
    # Valid zones in the city graph — the LLM must pick one of these
    VALID_ZONES = [
        "downtown", "harbor", "industrial", "sector7", "north_grid",
        "central_park", "westside", "port", "eastside", "suburbs",
        "midtown", "airport"
    ]
    zones_str = ", ".join(VALID_ZONES)

    system_prompt = f"""
    You are an emergency triage agent for a smart city dispatch system.
    You receive raw emergency 112 calls in Hinglish (Hindi + English).
    Your task is to extract structured information into JSON format.
    You must return ONLY valid JSON without any markdown formatting or extra text.
    
    CRITICAL RULE FOR LOCATION:
    The location MUST be exactly one of these city zones: {zones_str}
    If the caller mentions a specific area, map it to the closest matching zone.
    If the location is vague or unclear, default to "downtown".
    NEVER use "Unknown" or any value not in the list above.
    
    INCIDENT TYPE CLASSIFICATION:
    Classify as specifically as possible. Use these exact values:
    - "fire" — general fire
    - "accident" — vehicle accident
    - "flood" — water-related emergency
    - "earthquake" — seismic event
    - "medical" — medical emergency
    - "explosion" — blast or explosion event
    - "gas_leak" — gas leak reported
    - "building_collapse" — structural collapse
    - "chemical_spill" — chemical/hazmat spill

    If the fire involves a factory, industrial area, or chemicals, still use "fire" 
    but set has_chemical_hazard or has_industrial_context to true.
    
    Required JSON schema:
    {{
        "location": "string (MUST be one of: {zones_str})",
        "incident_type": "string (from the list above)",
        "severity": "string (must be exactly one of: low, medium, high, critical)",
        "injured_count": integer (number of injured people, 0 if none mentioned),
        "trapped_count": integer (number of trapped people, 0 if none mentioned),
        "resources_needed": ["list of strings (choose from: ambulance, fire_truck, police)"],
        "caller_summary": "string (plain English summary of the full situation)",
        "has_chemical_hazard": boolean (true if chemicals, toxic, gas, hazmat mentioned),
        "has_industrial_context": boolean (true if factory, industrial, plant, warehouse),
        "has_spread_risk": boolean (true if fire/flood/explosion is spreading or growing),
        "is_multi_casualty": boolean (true if multiple people are injured or at risk),
        "time_critical_indicators": "string (describe any urgency: cardiac arrest, heavy bleeding, trapped under debris, etc. Empty string if none)"
    }}

    SEVERITY GUIDELINES:
    - "low": Minor incident, no injuries, limited risk (e.g. weakness, small spill)
    - "medium": Moderate incident, few injuries, contained risk
    - "high": Serious incident, multiple injuries, spreading risk, people trapped
    - "critical": Major incident, mass casualties, chemical/explosion, large-scale
    
    Use "high" or "critical" when:
    - People are trapped
    - Chemicals or explosions are involved
    - Multiple casualties reported
    - Fire/flood is actively spreading
    - Critical infrastructure (airport, hospital) is affected
    """
    
    for call in raw_calls:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Transcript: {call}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_json = response.choices[0].message.content
            triage_data = json.loads(result_json)
            
            # Add required internal tracking fields
            triage_data["incident_id"] = str(uuid.uuid4())
            triage_data["raw_transcript"] = call

            # Ensure boolean fields have defaults
            triage_data.setdefault("has_chemical_hazard", False)
            triage_data.setdefault("has_industrial_context", False)
            triage_data.setdefault("has_spread_risk", False)
            triage_data.setdefault("is_multi_casualty", False)
            triage_data.setdefault("trapped_count", 0)
            triage_data.setdefault("time_critical_indicators", "")

            triage_outputs.append(triage_data)

            # Enhanced reasoning note
            flags = []
            if triage_data.get("has_chemical_hazard"):
                flags.append("HAZMAT")
            if triage_data.get("has_industrial_context"):
                flags.append("INDUSTRIAL")
            if triage_data.get("has_spread_risk"):
                flags.append("SPREADING")
            if triage_data.get("is_multi_casualty"):
                flags.append("MULTI-CASUALTY")
            if triage_data.get("trapped_count", 0) > 0:
                flags.append(f"{triage_data['trapped_count']} TRAPPED")

            flag_str = f" [{', '.join(flags)}]" if flags else ""
            reasoning_notes.append(
                f"Triaged '{triage_data.get('incident_type')}' at '{triage_data.get('location')}' "
                f"(Severity: {triage_data.get('severity')}, "
                f"Injured: {triage_data.get('injured_count', 0)}){flag_str}."
            )
            
        except Exception as e:
            # Graceful fallback for parsing or API errors
            fallback = {
                "incident_id": str(uuid.uuid4()),
                "location": "downtown",
                "incident_type": "unknown",
                "severity": "medium",
                "injured_count": 0,
                "trapped_count": 0,
                "resources_needed": ["police"], # Safest default
                "caller_summary": "Failed to parse transcript",
                "raw_transcript": call,
                "has_chemical_hazard": False,
                "has_industrial_context": False,
                "has_spread_risk": False,
                "is_multi_casualty": False,
                "time_critical_indicators": "",
            }
            triage_outputs.append(fallback)
            reasoning_notes.append(f"Failed to triage call due to error: {str(e)}")

    reasoning_summary = f"Triage Agent processed {len(raw_calls)} calls. Details: " + " ".join(reasoning_notes)
    
    # Update agent reasoning dictionary
    agent_reasoning = state.get("agent_reasoning", {})
    agent_reasoning["triage"] = reasoning_summary
    
    return {
        "triage_outputs": triage_outputs,
        "agent_reasoning": agent_reasoning,
        "status": "Triage Completed"
    }
