"""Structured logging for CrisisGrid AI backend.

Provides:
- JSON-structured log output in production
- Colored human-readable output in development
- Per-module logger factory
- Request-scoped context injection
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone, timedelta

from backend.core.config import get_settings

IST = timezone(timedelta(hours=5, minutes=30))


class CrisisGridFormatter(logging.Formatter):
    """Custom formatter with IST timestamps and emoji severity markers."""

    LEVEL_MARKERS = {
        "DEBUG": "🔍",
        "INFO": "ℹ️ ",
        "WARNING": "⚠️ ",
        "ERROR": "❌",
        "CRITICAL": "🔴",
    }

    def format(self, record: logging.LogRecord) -> str:
        ist_time = datetime.now(IST).strftime("%H:%M:%S")
        marker = self.LEVEL_MARKERS.get(record.levelname, "  ")
        module = record.name.split(".")[-1] if "." in record.name else record.name
        return f"{ist_time} | {marker} {record.levelname:<8s} | {module:<20s} | {record.getMessage()}"


def setup_logging() -> None:
    """Configure root logger for the application."""
    settings = get_settings()
    level = logging.DEBUG if settings.DEBUG else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers to avoid duplicates on reload
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(CrisisGridFormatter())
    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("groq").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger for a module."""
    return logging.getLogger(f"crisisgrid.{name}")
