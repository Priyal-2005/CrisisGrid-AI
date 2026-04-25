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
    Takes raw Hinglish calls and extracts structured JSON data.
    """
    raw_calls = state.get("raw_calls", [])
    if not raw_calls:
        return {"status": "No calls to triage"}
        
    groq_client = get_groq_client()
    triage_outputs = []
    reasoning_notes = []
    
    system_prompt = """
    You are an emergency triage agent. You receive raw emergency 112 calls in Hinglish (Hindi + English).
    Your task is to extract structured information into JSON format.
    You must return ONLY valid JSON without any markdown formatting or extra text.
    
    Required JSON schema:
    {
        "location": "string (extract the best guess for the location, standardizing vague terms like 'yahan' to 'Unknown' if no specific location is mentioned)",
        "incident_type": "string (must be exactly one of: fire, flood, accident, earthquake, medical)",
        "severity": "string (must be exactly one of: low, medium, critical)",
        "injured_count": integer (extract the number of injured people, 0 if none mentioned),
        "resources_needed": ["list of strings (choose from: ambulance, fire_truck, police)"],
        "caller_summary": "string (plain English summary of the situation)"
    }
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
            
            triage_outputs.append(triage_data)
            reasoning_notes.append(f"Triaged '{triage_data.get('incident_type')}' at '{triage_data.get('location')}' (Severity: {triage_data.get('severity')}).")
            
        except Exception as e:
            # Graceful fallback for parsing or API errors
            fallback = {
                "incident_id": str(uuid.uuid4()),
                "location": "Unknown",
                "incident_type": "unknown",
                "severity": "medium",
                "injured_count": 0,
                "resources_needed": ["police"], # Safest default
                "caller_summary": "Failed to parse transcript",
                "raw_transcript": call
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
