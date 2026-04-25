# %% [markdown]
# # 🚨 CrisisGrid AI — Backend
# Multi-agent emergency dispatch system powered by LangGraph + FastAPI.

# %% Cell 1: Install dependencies (Colab only)
# !pip install langgraph fastapi uvicorn pyngrok groq networkx nest_asyncio python-dotenv

# %% Cell 2: Imports
import os
import sys
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
load_dotenv()

import nest_asyncio
nest_asyncio.apply()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pyngrok import ngrok
import uvicorn

PROJECT_ROOT = os.getcwd()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from graph.workflow import run_pipeline_stateful
from data.mock_calls import MOCK_CALLS, TEST_SCENARIO
from data.city_graph import create_city_graph
from data.resources import load_resources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("crisisgrid")

IST = timezone(timedelta(hours=5, minutes=30))

# %% Cell 3: Initialize data
city_graph = create_city_graph()
resources = load_resources()

# ---------------------------------------------------------------------------
# Persistent global state — CUMULATIVE across all calls, never reset
# ---------------------------------------------------------------------------
incident_counter = 0

current_state: dict = {
    "raw_calls": [],
    "incidents": [],           # formatted for UI
    "resources": resources,    # live resource dict — shared mutable
    "dispatch_log": [],        # formatted for UI
    "agent_reasoning": {},
    "alerts": [],
    "live_feed": [],
    "city_graph": city_graph,
    # Raw pipeline-format data (for cross-incident context to agents)
    "_raw_incidents": [],
    "_raw_dispatch_log": [],
}

_seen_incident_ids: set = set()

logger.info("City graph: %d zones", len(city_graph.graph.nodes))
logger.info("Resources: %d units", len(resources))

# ---------------------------------------------------------------------------
# Type icon mapping
# ---------------------------------------------------------------------------
TYPE_ICON = {
    "fire": "🔥", "flood": "🌊", "earthquake": "🏚️",
    "accident": "💥", "medical": "🚑", "unknown": "⚠️",
}

def _get_icon(incident_type: str) -> str:
    return TYPE_ICON.get(incident_type.lower(), "⚠️")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_incident(raw_inc: dict, display_id: str, units: list, ts: str) -> dict:
    inc_type = raw_inc.get("incident_type", raw_inc.get("type", "Unknown"))
    location = raw_inc.get("location", "Unknown")
    severity = raw_inc.get("severity", "MEDIUM").upper()
    calls_merged = raw_inc.get("duplicate_count", raw_inc.get("calls_merged", 1))
    escalation = raw_inc.get("escalation_reason")

    desc = raw_inc.get("summary", raw_inc.get("description",
           f"{inc_type.title()} reported at {location}"))
    if escalation:
        desc = f"{desc} [{escalation}]"

    return {
        "id": display_id,
        "internal_id": raw_inc.get("id", raw_inc.get("master_incident_id", "")),
        "type": inc_type.title(),
        "location": location.replace("_", " ").title(),
        "severity": severity,
        "status": "ACTIVE",
        "units": units,
        "time": ts,
        "timestamp": ts,
        "description": desc,
        "calls_merged": calls_merged,
        "injured_count": raw_inc.get("injured_count", 0),
        "resources_needed": raw_inc.get("resources_needed", []),
        "confidence_score": raw_inc.get("confidence_score", 50),
        "escalated": escalation is not None,
    }


def _format_dispatch_entry(raw_entry: dict, display_inc_id: str) -> dict:
    route = raw_entry.get("route", [])
    route_str = (
        " → ".join(str(x).replace("_", " ").title() for x in route)
        if isinstance(route, list) else str(route)
    )
    eta = raw_entry.get("eta", 0)
    ts = raw_entry.get("timestamp", "")
    time_str = ts.split(" ")[1] if " " in ts else ts
    rerouted = raw_entry.get("rerouted_from")
    status = "REROUTED → EN ROUTE" if rerouted else "EN ROUTE"
    return {
        "time": time_str,
        "incident": display_inc_id,
        "incident_id": display_inc_id,
        "unit_id": raw_entry.get("unit_id", ""),
        "unit": raw_entry.get("unit_id", ""),
        "route": route_str,
        "eta": f"{eta:.0f} min" if isinstance(eta, (int, float)) else str(eta),
        "severity": raw_entry.get("severity", ""),
        "status": status,
        "rerouted_from": rerouted or "",
    }


def _humanize_reasoning(raw_reasoning: dict, context: str) -> dict:
    """Convert pipeline reasoning into rich, human-readable explanations."""
    result = {}

    triage_raw = raw_reasoning.get("triage", "")
    result["Triage Agent"] = (
        f"📞 Incoming 112 call processed.\n{context}\n\n"
        + (triage_raw if triage_raw else "No new calls processed.")
    )

    fusion_raw = raw_reasoning.get("fusion", "")
    result["Fusion Agent"] = (
        "🔗 Duplicate analysis and incident merging:\n\n"
        + (fusion_raw if fusion_raw else "Waiting for triage output.")
    )

    dispatch_raw = raw_reasoning.get("dispatch", "")
    result["Dispatch Agent"] = (
        "🚀 Resource routing decision:\n\n"
        + (dispatch_raw if dispatch_raw else "No dispatch actions taken.")
    )

    strategy_raw = raw_reasoning.get("strategy", "")
    result["Strategy Agent"] = (
        "🧠 Strategic assessment:\n\n"
        + (strategy_raw if strategy_raw else "Awaiting dispatch data.")
    )

    return result


# ---------------------------------------------------------------------------
# Re-routing logic (backend-level, post-pipeline)
# ---------------------------------------------------------------------------

def _attempt_backend_reroute(new_inc_display_id: str,
                               new_severity: str, resources_needed: list) -> dict | None:
    """
    If a new CRITICAL incident has no units dispatched,
    try to reassign a unit from a LOW incident at the backend level.

    Returns a new dispatch-log-like entry if re-routing succeeded, else None.
    """
    if new_severity.upper() != "CRITICAL":
        return None

    # Check if new incident already has dispatched units
    for entry in current_state["dispatch_log"]:
        if entry.get("incident") == new_inc_display_id or \
           entry.get("incident_id") == new_inc_display_id:
            return None  # already has units

    # Build resource type needed
    TYPE_MAP = {
        "fire": "fire_truck", "Fire": "fire_truck", "fire_truck": "fire_truck",
        "Fire Truck": "fire_truck", "ambulance": "ambulance", "Ambulance": "ambulance",
        "Medical": "ambulance", "medical": "ambulance", "police": "police", "Police": "police",
    }
    needed_types = set()
    for need in resources_needed:
        t = TYPE_MAP.get(need)
        if t:
            needed_types.add(t)
    if not needed_types:
        return None

    # Find a LOW incident with a dispatched unit of the right type
    low_incidents = {
        inc["id"]: inc for inc in current_state["incidents"]
        if inc.get("severity", "LOW").upper() == "LOW"
    }
    if not low_incidents:
        return None

    for entry in reversed(current_state["dispatch_log"]):
        donor_inc_id = entry.get("incident")
        unit_id = entry.get("unit") or entry.get("unit_id")
        if donor_inc_id not in low_incidents:
            continue
        if not unit_id or unit_id not in current_state["resources"]:
            continue
        unit = current_state["resources"][unit_id]
        if unit.get("status") != "DISPATCHED":
            continue
        if unit.get("type") not in needed_types:
            continue

        # Execute reassignment
        current_state["resources"][unit_id]["status"] = "DISPATCHED"
        current_state["resources"][unit_id]["assigned_incident"] = new_inc_display_id

        now_str = datetime.now(IST).strftime("%H:%M:%S")
        reroute_entry = {
            "time": now_str,
            "incident": new_inc_display_id,
            "incident_id": new_inc_display_id,
            "unit": unit_id,
            "unit_id": unit_id,
            "route": f"[REROUTED from {donor_inc_id}]",
            "eta": "Redirecting...",
            "severity": "CRITICAL",
            "status": "REROUTED → EN ROUTE",
            "rerouted_from": donor_inc_id,
        }
        current_state["dispatch_log"].append(reroute_entry)

        logger.info(
            "🔄 REROUTED %s: pulled from LOW incident %s → CRITICAL %s",
            unit_id, donor_inc_id, new_inc_display_id,
        )

        # Update agent reasoning to reflect this
        existing_dispatch = current_state["agent_reasoning"].get("Dispatch Agent", "")
        current_state["agent_reasoning"]["Dispatch Agent"] = (
            existing_dispatch + f"\n\n🔄 BACKEND REROUTE: {unit_id} reassigned from "
            f"LOW incident {donor_inc_id} to CRITICAL {new_inc_display_id}. "
            f"Reason: CRITICAL incidents preempt LOW priority dispatches."
        )

        return reroute_entry

    return None


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

class CallRequest(BaseModel):
    transcript: str


app = FastAPI(
    title="CrisisGrid AI Backend",
    description="Multi-agent emergency dispatch — LangGraph powered.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Core call processing
# ---------------------------------------------------------------------------

async def _process_transcript(transcript: str) -> dict:
    """
    Run the full LangGraph pipeline for one transcript and merge results
    into the persistent current_state. Returns the updated response dict.
    """
    global current_state, incident_counter

    current_state["raw_calls"].append(transcript)

    result = run_pipeline_stateful(
        state=current_state,
        transcript=transcript,
    )

    now_str = datetime.now(IST).strftime("%H:%M:%S")

    # Deduplicate raw pipeline output (LangGraph operator.add can produce dupes)
    raw_incidents = result.get("incidents", [])
    seen_this_run: set = set()
    deduped_incidents = []
    for inc in raw_incidents:
        iid = inc.get("id", inc.get("master_incident_id", ""))
        if iid and iid not in seen_this_run:
            seen_this_run.add(iid)
            deduped_incidents.append(inc)

    raw_log = result.get("dispatch_log", [])
    seen_log: set = set()
    deduped_log = []
    for entry in raw_log:
        key = (entry.get("incident_id"), entry.get("unit_id"), entry.get("timestamp"))
        if key not in seen_log:
            seen_log.add(key)
            deduped_log.append(entry)

    # Map internal incident ID → assigned unit IDs
    unit_map: dict[str, list[str]] = {}
    for entry in deduped_log:
        iid = entry.get("incident_id", "")
        uid = entry.get("unit_id", "")
        if iid and uid:
            unit_map.setdefault(iid, []).append(uid)

    # Merge new incidents into persistent state (skip already-seen)
    new_feed_events = []
    for inc in deduped_incidents:
        iid = inc.get("id", inc.get("master_incident_id", ""))
        if iid in _seen_incident_ids:
            continue
        _seen_incident_ids.add(iid)

        incident_counter += 1
        display_id = f"INC-{incident_counter:03d}"
        units = unit_map.get(iid, [])

        formatted = _format_incident(inc, display_id, units, now_str)
        current_state["incidents"].append(formatted)
        current_state["_raw_incidents"].append(inc)

        icon = _get_icon(inc.get("incident_type", "unknown"))
        severity = inc.get("severity", "MEDIUM").upper()
        calls_merged = inc.get("duplicate_count", 1)
        escalated = inc.get("escalation_reason") is not None

        feed_msg = (
            f"🚨 {icon} {formatted['type']} at {formatted['location']} "
            f"[{severity}]"
            + (f" — {calls_merged} calls merged" if calls_merged > 1 else "")
            + (" ⬆️ AUTO-ESCALATED" if escalated else "")
        )
        new_feed_events.append(feed_msg)

        for uid in units:
            entry_for_unit = next(
                (e for e in deduped_log
                 if e.get("unit_id") == uid and e.get("incident_id") == iid),
                None,
            )
            eta_str = (
                f" (ETA: {entry_for_unit['eta']:.0f} min)"
                if entry_for_unit and isinstance(entry_for_unit.get("eta"), (int, float))
                else ""
            )
            new_feed_events.append(f"🚑 {uid} dispatched → {formatted['location']}{eta_str}")

        # Add formatted dispatch entries
        for entry in deduped_log:
            if entry.get("incident_id") == iid:
                current_state["dispatch_log"].append(
                    _format_dispatch_entry(entry, display_id)
                )
                current_state["_raw_dispatch_log"].append(entry)

        # Attempt backend-level re-routing for CRITICAL incidents with no units
        if severity == "CRITICAL" and not units:
            reroute = _attempt_backend_reroute(
                display_id, severity,
                inc.get("resources_needed", []),
            )
            if reroute:
                new_feed_events.append(
                    f"🔄 REROUTED {reroute['unit']} → {display_id} "
                    f"[pulled from LOW incident {reroute['rerouted_from']}]"
                )

    # --- Resource strain check ---
    total_units = len(current_state["resources"])
    dispatched_count = sum(1 for u in current_state["resources"].values() if u.get("status") == "DISPATCHED")
    if total_units > 0 and dispatched_count / total_units > 0.6:
        new_feed_events.append(f"⚠️ Resource strain: {dispatched_count}/{total_units} units deployed — prioritizing CRITICAL incidents")

    # Always update resources from latest pipeline result
    pipeline_resources = result.get("resources", {})
    if pipeline_resources:
        current_state["resources"] = pipeline_resources

    # Update reasoning
    raw_reasoning = result.get("agent_reasoning", {})
    n_incidents = len(current_state["incidents"])
    n_dispatched = sum(
        1 for u in current_state["resources"].values()
        if u.get("status") == "DISPATCHED"
    )
    context = (
        f"System state: {n_incidents} cumulative incident(s) | "
        f"{n_dispatched}/{len(current_state['resources'])} units deployed"
    )
    current_state["agent_reasoning"] = _humanize_reasoning(raw_reasoning, context)

    # Update alerts
    new_alerts = result.get("alerts", [])
    for alert in new_alerts:
        if alert not in current_state["alerts"]:
            current_state["alerts"].append(alert)
            new_feed_events.append(f"⚠️ {alert}")

    # Live feed — newest first, cap at 25
    current_state["live_feed"] = (
        new_feed_events + current_state.get("live_feed", [])
    )[:25]

    logger.info(
        "✅ Pipeline done — %d incident(s) total, %d dispatch(es) total",
        len(current_state["incidents"]),
        len(current_state["dispatch_log"]),
    )

    return _build_response()


@app.post("/process-call")
async def process_call(data: CallRequest):
    """Process a single emergency call through the full 4-agent pipeline."""
    logger.info("📞 Call: %s...", data.transcript[:80])
    try:
        return await _process_transcript(data.transcript)
    except Exception as exc:
        logger.error("❌ Pipeline error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Live simulation
# ---------------------------------------------------------------------------

async def run_live_simulation(
    calls: list[str] | None = None,
    delay_seconds: float = 2.0,
) -> list[dict]:
    """
    Auto-trigger mock calls sequentially with delay.
    Accumulates results in persistent state.

    Args:
        calls: List of transcripts to process. Defaults to MOCK_CALLS.
        delay_seconds: Pause between calls.

    Returns:
        List of response dicts, one per call.
    """
    calls_to_run = calls or MOCK_CALLS
    results = []
    for i, transcript in enumerate(calls_to_run):
        logger.info("🔁 Simulation call %d/%d", i + 1, len(calls_to_run))
        response = await _process_transcript(transcript)
        results.append(response)
        if i < len(calls_to_run) - 1:
            await asyncio.sleep(delay_seconds)
    logger.info("✅ Simulation complete — %d calls processed", len(calls_to_run))
    return results


@app.post("/simulate")
async def simulate(delay: float = 2.0):
    """
    Run all MOCK_CALLS sequentially through the pipeline.
    Demonstrates multi-incident accumulation, merging, and prioritization.
    """
    logger.info("🎬 Starting full simulation (%d calls)", len(MOCK_CALLS))
    results = await run_live_simulation(delay_seconds=delay)
    return {
        "message": f"Simulation complete — {len(results)} calls processed",
        "state": _build_response(),
    }


@app.post("/run-scenario")
async def run_scenario(delay: float = 1.5):
    """
    Run the structured 6-call test scenario:
    1. Fire (CRITICAL) → 2. Duplicate fire → 3. Third fire (auto-escalates) →
    4. Accident (CRITICAL) → 5. Medical (LOW) → 6. CRITICAL explosion (scarce resources)

    Verifies: merging, escalation, prioritization, re-routing.
    """
    global current_state, incident_counter, _seen_incident_ids

    # Reset state for clean scenario run
    resources_fresh = load_resources()
    incident_counter = 0
    _seen_incident_ids = set()
    current_state.update({
        "raw_calls": [],
        "incidents": [],
        "resources": resources_fresh,
        "dispatch_log": [],
        "agent_reasoning": {},
        "alerts": [],
        "live_feed": [],
        "_raw_incidents": [],
        "_raw_dispatch_log": [],
    })

    results = []

    for i, step in enumerate(TEST_SCENARIO):
        logger.info("📋 Scenario step %d: %s", i + 1, step["description"])
        await _process_transcript(step["call"])
        results.append({
            "step": i + 1,
            "description": step["description"],
            "expected_type": step["expected_type"],
            "expected_severity": step["expected_severity"],
            "incidents_so_far": len(current_state["incidents"]),
            "dispatches_so_far": len(current_state["dispatch_log"]),
            "alerts": list(current_state["alerts"]),
        })
        if i < len(TEST_SCENARIO) - 1:
            await asyncio.sleep(delay)

    return {
        "message": "Test scenario complete",
        "steps": results,
        "final_state": _build_response(),
    }


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

def _build_response() -> dict:
    """Serialize current_state for the dashboard API."""
    res_list = []
    for uid, info in current_state["resources"].items():
        r = {"id": uid, **info}
        # Attach dispatch info
        for entry in current_state["dispatch_log"]:
            if entry.get("unit") == uid or entry.get("unit_id") == uid:
                r["assigned_incident"] = entry.get("incident", "")
                r["eta_display"] = entry.get("eta", "")
                break
        res_list.append(r)

    return {
        "incidents": current_state["incidents"],
        "resources": res_list,
        "dispatch_log": current_state["dispatch_log"],
        "agent_reasoning": current_state["agent_reasoning"],
        "alerts": current_state.get("alerts", []),
        "live_feed": current_state.get("live_feed", []),
        "stats": {
            "total_incidents": len(current_state["incidents"]),
            "total_dispatches": len(current_state["dispatch_log"]),
            "units_deployed": sum(
                1 for u in current_state["resources"].values()
                if u.get("status") == "DISPATCHED"
            ),
            "utilization": round(
                sum(1 for u in current_state["resources"].values()
                    if u.get("status") == "DISPATCHED")
                / max(len(current_state["resources"]), 1), 2
            ),
        }
    }


@app.get("/state")
async def get_full_state():
    return _build_response()


@app.get("/incidents")
async def get_incidents():
    return {"incidents": current_state["incidents"]}


@app.get("/resources")
async def get_resources():
    return {"resources": [{"id": uid, **info}
                           for uid, info in current_state["resources"].items()]}


@app.get("/dispatch-log")
async def get_dispatch_log():
    return {"dispatch_log": current_state["dispatch_log"]}


@app.get("/alerts")
async def get_alerts():
    return {"alerts": current_state.get("alerts", [])}


@app.get("/mock-calls")
async def get_mock_calls():
    return {"calls": MOCK_CALLS}


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "incidents": len(current_state["incidents"]),
        "resources": len(current_state["resources"]),
    }


@app.post("/reset")
async def reset_state():
    """Reset all state back to initial resources. Useful for demo restarts."""
    global current_state, incident_counter, _seen_incident_ids
    resources_fresh = load_resources()
    incident_counter = 0
    _seen_incident_ids = set()
    current_state.update({
        "raw_calls": [],
        "incidents": [],
        "resources": resources_fresh,
        "dispatch_log": [],
        "agent_reasoning": {},
        "alerts": [],
        "live_feed": ["🔄 System reset — all resources restored to AVAILABLE"],
        "_raw_incidents": [],
        "_raw_dispatch_log": [],
    })
    logger.info("🔄 State reset to initial configuration")
    return {"message": "State reset successfully", "resources": len(resources_fresh)}


# %% Cell 5: Launch server
ngrok_auth = os.getenv("NGROK_AUTH_TOKEN")
if ngrok_auth:
    ngrok.set_auth_token(ngrok_auth)
else:
    logger.warning("⚠️  NGROK_AUTH_TOKEN not set — tunnel may fail on free tier.")

tunnels = ngrok.get_tunnels()
if tunnels:
    public_url = tunnels[0].public_url
    logger.info("🔌 Existing ngrok tunnel: %s", public_url)
else:
    public_url = ngrok.connect(8000).public_url
    logger.info("🔌 New ngrok tunnel: %s", public_url)

print()
print("=" * 60)
print("🚨 CrisisGrid AI Backend — LIVE")
print(f"🌐 Public URL  : {public_url}")
print(f"📖 API Docs    : {public_url}/docs")
print(f"🎬 Run scenario: POST {public_url}/run-scenario")
print(f"🔁 Simulate    : POST {public_url}/simulate")
print(f"🔄 Reset       : POST {public_url}/reset")
print(f"🕐 Started     : {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST")
print("=" * 60)
print()

try:
    uvicorn.run(app, host="0.0.0.0", port=8000)
except KeyboardInterrupt:
    logger.info("🛑 Server stopped.")
except Exception as exc:
    logger.error("🛑 Crash: %s", exc, exc_info=True)
finally:
    ngrok.disconnect(public_url)
    logger.info("🔌 ngrok tunnel closed.")
