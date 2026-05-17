"""Centralized configuration — environment variables, constants, feature flags.

Single source of truth for all backend settings.
Uses pydantic-settings for validation and .env loading.
"""

from __future__ import annotations

import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # ── Server ──
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENV: str = os.getenv("ENV", "production")

    # ── CORS ──
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # ── LLM ──
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL_TRIAGE: str = os.getenv("LLM_MODEL_TRIAGE", "llama-3.3-70b-versatile")
    LLM_MODEL_STRATEGY: str = os.getenv("LLM_MODEL_STRATEGY", "llama-3.1-8b-instant")

    # ── Simulation ──
    DEFAULT_SIMULATION_DELAY: float = float(os.getenv("SIMULATION_DELAY", "2.0"))
    SCENARIO_DELAY: float = float(os.getenv("SCENARIO_DELAY", "1.5"))

    # ── Limits ──
    MAX_LIVE_FEED_ENTRIES: int = int(os.getenv("MAX_LIVE_FEED", "50"))
    RESOURCE_STRAIN_THRESHOLD: float = float(os.getenv("RESOURCE_STRAIN_THRESHOLD", "0.6"))
    UTILIZATION_WARNING_THRESHOLD: float = float(os.getenv("UTILIZATION_WARNING", "0.75"))

    # ── WebSocket ──
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))

    # ── API ──
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "CrisisGrid AI"
    VERSION: str = "4.0.0"
    DESCRIPTION: str = "Production-grade multi-agent emergency dispatch system"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
