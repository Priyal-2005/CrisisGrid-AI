# %% [markdown]
# # 🚨 CrisisGrid AI — Colab Backend
# Runs the LangGraph multi-agent pipeline and exposes it via FastAPI + ngrok.

# %% Cell 1: Install dependencies
# !pip install langgraph fastapi uvicorn pyngrok groq networkx anthropic nest_asyncio

# %% Cell 2: Imports and setup
import os
import sys
import logging
from datetime import datetime

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

# %% Cell 3: Initialize data
city_graph = create_city_graph()
resources = load_resources()

# Mutable server state — updated after every pipeline run
current_state: dict = {
    "incidents": [],
    "resources": resources,
    "dispatch_log": [],
    "agent_reasoning": {},
    "alerts": [],
}

logger.info("City graph loaded: %d zones", len(city_graph.graph.nodes))
logger.info("Resources loaded: %d units", len(resources))


# %% Cell 4: FastAPI application
class CallRequest(BaseModel):
    """Request body for /process-call."""
    transcript: str


app = FastAPI(
    title="CrisisGrid AI Backend",
    description="Multi-agent emergency dispatch system powered by LangGraph.",
    version="1.0.0",
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

    Runs Triage → Fusion → Dispatch → Strategy and returns the
    aggregated results.
    """
    global current_state

    logger.info("📞 Incoming call: %s...", data.transcript[:80])

    try:
        result = run_pipeline(
            transcript=data.transcript,
            resources=current_state["resources"],
            city_graph=city_graph,
        )

        # Deduplicate incidents (LangGraph operator.add causes repeats)
        raw_incidents = result.get("incidents", [])
        seen_ids = set()
        deduped_incidents = []
        for inc in raw_incidents:
            iid = inc.get("id", inc.get("master_incident_id"))
            if iid not in seen_ids:
                seen_ids.add(iid)
                deduped_incidents.append(inc)

        raw_log = result.get("dispatch_log", [])
        seen_log = set()
        deduped_log = []
        for entry in raw_log:
            key = (entry.get("incident_id"), entry.get("unit_id"), entry.get("timestamp"))
            if key not in seen_log:
                seen_log.add(key)
                deduped_log.append(entry)

        # Merge pipeline output into server state
        current_state["incidents"] = deduped_incidents or current_state["incidents"]
        current_state["resources"] = result.get("resources", current_state["resources"])
        current_state["dispatch_log"] = deduped_log or current_state["dispatch_log"]
        current_state["agent_reasoning"] = result.get("agent_reasoning", current_state["agent_reasoning"])
        current_state["alerts"] = result.get("alerts", current_state.get("alerts", []))

        logger.info(
            "✅ Pipeline complete — %d incident(s), %d dispatch(es)",
            len(current_state["incidents"]),
            len(current_state["dispatch_log"]),
        )

        return {
            "incidents": current_state["incidents"],
            "resources": [{"id": k, **v} for k, v in current_state["resources"].items()],
            "dispatch_log": current_state["dispatch_log"],
            "agent_reasoning": current_state["agent_reasoning"],
        }

    except Exception as exc:
        logger.error("❌ Pipeline error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/incidents")
async def get_incidents():
    """Return all current incidents."""
    logger.info("📋 GET /incidents")
    return {"incidents": current_state["incidents"]}


@app.get("/resources")
async def get_resources():
    """Return current resource statuses."""
    logger.info("📋 GET /resources")
    return {"resources": [{"id": k, **v} for k, v in current_state["resources"].items()]}


@app.get("/dispatch-log")
async def get_dispatch_log():
    """Return dispatch history."""
    logger.info("📋 GET /dispatch-log")
    return {"dispatch_log": current_state["dispatch_log"]}


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
print(f"🕐 Started at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
