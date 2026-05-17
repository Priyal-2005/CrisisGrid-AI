"""Main FastAPI application entrypoint."""

from __future__ import annotations

import os
import sys

# Ensure project root is in sys.path for Render deployment
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.core.logging import setup_logging, get_logger
from backend.core.state import get_state_manager
from backend.middleware.error_handler import ErrorHandlerMiddleware, RequestLoggingMiddleware
from backend.api.v1 import incidents, simulation, system
from backend.api import ws
from backend.schemas.models import HealthResponse

# Initialize configuration and logging
settings = get_settings()
setup_logging()
logger = get_logger("main")

# Pre-warm state on startup
_ = get_state_manager()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    debug=settings.DEBUG,
)

# ── Middleware ──
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──
app.include_router(incidents.router, prefix=settings.API_V1_PREFIX)
app.include_router(simulation.router, prefix=settings.API_V1_PREFIX)
app.include_router(system.router, prefix=settings.API_V1_PREFIX)
app.include_router(ws.router)

# ── Base Routes ──

START_TIME = time.time()

@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.get(f"{settings.API_V1_PREFIX}/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """System health check endpoint."""
    state = get_state_manager()
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        incidents=len(state.incidents),
        resources=len(state.resources),
        uptime_seconds=round(time.time() - START_TIME, 2)
    )

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting %s v%s", settings.PROJECT_NAME, settings.VERSION)
    logger.info("🌐 API prefix: %s", settings.API_V1_PREFIX)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Shutting down %s", settings.PROJECT_NAME)
