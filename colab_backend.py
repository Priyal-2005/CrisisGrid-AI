# %% [markdown]
# # 🚨 CrisisGrid AI — Colab Backend
# Runs the LangGraph multi-agent pipeline and exposes it via FastAPI + ngrok.

# %% Cell 1: Install dependencies
# !pip install langgraph fastapi uvicorn pyngrok groq networkx anthropic nest_asyncio

# %% Cell 2: Imports and setup
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
load_dotenv()  # Load GROQ_API_KEY, NGROK_AUTH_TOKEN from .env

import nest_asyncio
nest_asyncio.apply()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pyngrok import ngrok
import uvicorn

# Add project root to path so module imports work in Colab
PROJECT_ROOT = os.getcwd()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from graph.workflow import run_pipeline
from data.city_graph import create_city_graph
from data.resources import load_resources

# Logging
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
# Persistent global state — accumulates across calls, never overwritten
# ---------------------------------------------------------------------------
incident_counter = 0  # incremental display IDs

current_state: dict = {
    "incidents": [],         # list of formatted incident dicts
    "resources": resources,  # live resource dict
    "dispatch_log": [],      # list of formatted dispatch entries
    "agent_reasoning": {},   # latest reasoning per agent
    "alerts": [],            # system alerts
    "live_feed": [],         # latest events for live feed banner
}

# Track seen incident UUIDs to prevent duplicates
_seen_incident_ids: set = set()

logger.info("City graph loaded: %d zones", len(city_graph.graph.nodes))
logger.info("Resources loaded: %d units", len(resources))


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
TYPE_ICON = {
    "fire": "🔥", "flood": "🌊", "earthquake": "🏚️",
    "accident": "💥", "medical": "🚑",
}

def _get_icon(incident_type: str) -> str:
    return TYPE_ICON.get(incident_type.lower(), "⚠️")

def _format_incident(raw_inc: dict, display_id: str, units: list, ts: str) -> dict:
    """Convert a raw pipeline incident into a UI-friendly dict."""
    inc_type = raw_inc.get("incident_type", raw_inc.get("type", "Unknown"))
    location = raw_inc.get("location", "Unknown")
    severity = raw_inc.get("severity", "medium").upper()
    return {
        "id": display_id,
        "internal_id": raw_inc.get("id", raw_inc.get("master_incident_id", "")),
        "type": inc_type.title(),
        "location": location.replace("_", " ").title(),
        "severity": severity,
        "status": "ACTIVE",
        "units": units,
        "time": ts,
        "description": raw_inc.get("summary", raw_inc.get("description", f"{inc_type.title()} reported at {location}")),
        "calls_merged": raw_inc.get("duplicate_count", 1),
        "injured_count": raw_inc.get("injured_count", 0),
        "resources_needed": raw_inc.get("resources_needed", []),
    }

def _format_dispatch_entry(raw_entry: dict, display_id: str) -> dict:
    """Convert a raw dispatch log entry into a UI-friendly dict."""
    route = raw_entry.get("route", [])
    if isinstance(route, list):
        route_str = " → ".join(str(x).replace("_", " ").title() for x in route)
    else:
        route_str = str(route)
    eta = raw_entry.get("eta", 0)
    ts = raw_entry.get("timestamp", "")
    time_str = ts.split(" ")[1] if " " in ts else ts
    return {
        "time": time_str,
        "incident": display_id,
        "unit": raw_entry.get("unit_id", ""),
        "route": route_str,
        "eta": f"{eta:.0f} min" if isinstance(eta, (int, float)) else str(eta),
        "status": "EN ROUTE",
    }

def _humanize_reasoning(raw_reasoning: dict, incidents_summary: str) -> dict:
    """Convert technical agent reasoning into human-friendly explanations."""
    result = {}

    triage_raw = raw_reasoning.get("triage", "")
    if triage_raw:
        result["Triage Agent"] = f"📞 Incoming 112 call processed.\n{triage_raw}"
    else:
        result["Triage Agent"] = "📞 No calls processed yet."

    fusion_raw = raw_reasoning.get("fusion", "")
    if fusion_raw:
        result["Fusion Agent"] = f"🔗 Duplicate analysis complete.\n{fusion_raw}"
    else:
        result["Fusion Agent"] = "🔗 Waiting for triage data."

    dispatch_raw = raw_reasoning.get("dispatch", "")
    if dispatch_raw:
        result["Dispatch Agent"] = f"🚀 Resource routing decision:\n{dispatch_raw}"
    else:
        result["Dispatch Agent"] = "🚀 No dispatch actions taken."

    strategy_raw = raw_reasoning.get("strategy", "")
    if strategy_raw:
        result["Strategy Agent"] = f"🧠 Strategic assessment:\n{strategy_raw}"
    else:
        result["Strategy Agent"] = "🧠 Awaiting dispatch data for strategic review."

    return result


# %% Cell 4: FastAPI application
class CallRequest(BaseModel):
    """Request body for /process-call."""
    transcript: str


app = FastAPI(
    title="CrisisGrid AI Backend",
    description="Multi-agent emergency dispatch system powered by LangGraph.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/process-call")
async def process_call(data: CallRequest):
    """Process an emergency call transcript through the full pipeline.

    Runs Triage → Fusion → Dispatch → Strategy and merges results
    into the persistent global state. Incidents accumulate — no overwriting.
    """
    global current_state, incident_counter

    logger.info("📞 Incoming call: %s...", data.transcript[:80])

    try:
        result = run_pipeline(
            transcript=data.transcript,
            resources=current_state["resources"],
            city_graph=city_graph,
        )

        now_str = datetime.now(IST).strftime("%H:%M:%S")

        # --- Deduplicate raw pipeline output (LangGraph operator.add dupes) ---
        raw_incidents = result.get("incidents", [])
        seen_ids_this_run = set()
        deduped_incidents = []
        for inc in raw_incidents:
            iid = inc.get("id", inc.get("master_incident_id"))
            if iid and iid not in seen_ids_this_run:
                seen_ids_this_run.add(iid)
                deduped_incidents.append(inc)

        raw_log = result.get("dispatch_log", [])
        seen_log = set()
        deduped_log = []
        for entry in raw_log:
            key = (entry.get("incident_id"), entry.get("unit_id"), entry.get("timestamp"))
            if key not in seen_log:
                seen_log.add(key)
                deduped_log.append(entry)

        # --- Build a map from internal incident ID → assigned units ---
        unit_map: dict[str, list[str]] = {}
        for entry in deduped_log:
            iid = entry.get("incident_id", "")
            uid = entry.get("unit_id", "")
            if iid and uid:
                unit_map.setdefault(iid, []).append(uid)

        # --- Merge new incidents into persistent state ---
        new_feed_events = []
        for inc in deduped_incidents:
            iid = inc.get("id", inc.get("master_incident_id"))
            if iid in _seen_incident_ids:
                continue  # already tracked
            _seen_incident_ids.add(iid)

            incident_counter += 1
            display_id = f"INC-{incident_counter:03d}"
            units = unit_map.get(iid, [])

            formatted = _format_incident(inc, display_id, units, now_str)
            current_state["incidents"].append(formatted)

            # Live feed event
            icon = _get_icon(inc.get("incident_type", ""))
            new_feed_events.append(
                f"🚨 {icon} {formatted['type']} detected at {formatted['location']}"
            )
            for uid in units:
                entry_for_unit = next(
                    (e for e in deduped_log if e.get("unit_id") == uid and e.get("incident_id") == iid),
                    None,
                )
                eta_str = ""
                if entry_for_unit:
                    eta_str = f" (ETA: {entry_for_unit.get('eta', '?'):.0f} min)"
                new_feed_events.append(f"🚑 Dispatching {uid} → {formatted['location']}{eta_str}")

            # Format dispatch log entries for this incident
            for entry in deduped_log:
                if entry.get("incident_id") == iid:
                    current_state["dispatch_log"].append(
                        _format_dispatch_entry(entry, display_id)
                    )

        # --- Update resources (always take latest from pipeline) ---
        current_state["resources"] = result.get("resources", current_state["resources"])

        # --- Update reasoning (latest run) ---
        raw_reasoning = result.get("agent_reasoning", {})
        current_state["agent_reasoning"] = _humanize_reasoning(
            raw_reasoning,
            f"{len(current_state['incidents'])} total incidents",
        )

        # --- Update alerts ---
        current_state["alerts"] = result.get("alerts", current_state.get("alerts", []))

        # --- Live feed ---
        current_state["live_feed"] = new_feed_events + current_state.get("live_feed", [])
        current_state["live_feed"] = current_state["live_feed"][:20]  # keep last 20

        logger.info(
            "✅ Pipeline complete — %d incident(s), %d dispatch(es)",
            len(current_state["incidents"]),
            len(current_state["dispatch_log"]),
        )

        return _build_response()

    except Exception as exc:
        logger.error("❌ Pipeline error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


def _build_response() -> dict:
    """Build the standard API response from current_state."""
    # Format resources as list for UI
    res_list = []
    for uid, info in current_state["resources"].items():
        r = {"id": uid, **info}
        # Find if this unit is assigned to any dispatch
        for entry in current_state["dispatch_log"]:
            if entry.get("unit") == uid:
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
    }


@app.get("/incidents")
async def get_incidents():
    """Return all current incidents."""
    logger.info("📋 GET /incidents")
    return {"incidents": current_state["incidents"]}


@app.get("/resources")
async def get_resources():
    """Return current resource statuses."""
    logger.info("📋 GET /resources")
    res_list = []
    for uid, info in current_state["resources"].items():
        res_list.append({"id": uid, **info})
    return {"resources": res_list}


@app.get("/dispatch-log")
async def get_dispatch_log():
    """Return dispatch history."""
    logger.info("📋 GET /dispatch-log")
    return {"dispatch_log": current_state["dispatch_log"]}


@app.get("/state")
async def get_full_state():
    """Return full system state for the dashboard."""
    logger.info("📋 GET /state")
    return _build_response()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# %% Cell 5: Start ngrok tunnel and run server
ngrok_auth = os.getenv("NGROK_AUTH_TOKEN")
if ngrok_auth:
    ngrok.set_auth_token(ngrok_auth)
else:
    logger.warning("⚠️  NGROK_AUTH_TOKEN not set — tunnel may fail on free tier.")

tunnels = ngrok.get_tunnels()
if tunnels:
    public_url = tunnels[0].public_url
    logger.info("🔌 Found active ngrok tunnel: %s", public_url)
else:
    public_url = ngrok.connect(8000).public_url
    logger.info("🔌 Started new ngrok tunnel: %s", public_url)

print()
print("=" * 60)
print("🚀 CrisisGrid AI Backend is LIVE")
print(f"🌐 Public URL : {public_url}")
print(f"📖 API Docs   : {public_url}/docs")
print(f"🕐 Started at : {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST")
print("=" * 60)
print()

try:
    uvicorn.run(app, host="0.0.0.0", port=8000)
except KeyboardInterrupt:
    logger.info("🛑 Server stopped by user.")
except Exception as exc:
    logger.error("🛑 Server crashed: %s", exc, exc_info=True)
finally:
    ngrok.disconnect(public_url)
    logger.info("🔌 ngrok tunnel closed.")
