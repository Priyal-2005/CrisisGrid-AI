import os
import json
import uuid
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def get_groq_client():
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))

def fusion_agent(state):
    """
    LangGraph node function for Fusing triaged calls.
    Takes triaged outputs, merges duplicates, and creates master incidents.
    """
    triage_outputs = state.get("triage_outputs", [])
    if not triage_outputs:
        return {"status": "Fusion Skipped (No triage outputs)"}
        
    groq_client = get_groq_client()
    
    system_prompt = """
    You are an emergency Fusion Agent. You receive a list of triaged emergency incidents represented as JSON objects.
    Some of these incidents are duplicates reporting the exact same event (e.g., same fire at the same location, even if described slightly differently like 'harbour' vs 'Harbor District').
    
    Your task is to group these duplicates and merge them into a single master incident per real-world event.
    When merging duplicates:
    1. Resolve conflicts: Always take the highest severity (critical > medium > low).
    2. Combine resources: Take the union of all resources_needed.
    3. Injured count: Take the highest injured_count reported among the duplicates.
    4. Location: Pick the most specific, clear location name.
    
    For each master incident, add:
    - "duplicate_count": integer (how many calls reported this exact incident)
    - "confidence_score": integer (0-100, how confident you are they are the same incident)
    
    Return ONLY a valid JSON object containing a single key "incidents" mapped to a list of the merged master incident objects.
    Each master incident should look like this:
    {
      "master_incident_id": "new uuid string",
      "location": "string",
      "incident_type": "string",
      "severity": "string",
      "injured_count": integer,
      "resources_needed": ["string"],
      "duplicate_count": integer,
      "confidence_score": integer,
      "summary": "Plain English summary combining details from all callers"
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
        
        # Ensure UUIDs exist
        for inc in incidents:
            if "master_incident_id" not in inc:
                inc["master_incident_id"] = str(uuid.uuid4())
            inc["id"] = inc.get("master_incident_id", str(uuid.uuid4()))
                
        reasoning_summary = f"Fusion Agent grouped {len(triage_outputs)} triaged calls into {len(incidents)} unique master incidents."
        
    except Exception as e:
        # Fallback: pass through triaged outputs as separate incidents if LLM fails
        incidents = []
        for t in triage_outputs:
            inc = dict(t)
            inc["master_incident_id"] = str(uuid.uuid4())
            inc["id"] = inc.get("master_incident_id", str(uuid.uuid4()))
            inc["duplicate_count"] = 1
            inc["confidence_score"] = 0
            inc["summary"] = t.get("caller_summary", "")
            incidents.append(inc)
            
        reasoning_summary = f"Fusion Agent failed to merge calls due to error: {str(e)}. Passed through {len(incidents)} incidents without merging."

    agent_reasoning = state.get("agent_reasoning", {})
    agent_reasoning["fusion"] = reasoning_summary
    
    incident = incidents[0] if incidents else {}
    
    return {
        "incidents": incidents,
        "incident": incident,
        "agent_reasoning": agent_reasoning,
        "status": "Fusion Completed"
    }
