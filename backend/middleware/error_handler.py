"""Centralized exception handling middleware.

Catches unhandled exceptions and returns structured JSON error responses
instead of raw 500 errors. Also logs errors with full tracebacks.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone, timedelta

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.logging import get_logger

logger = get_logger("middleware")
IST = timezone(timedelta(hours=5, minutes=30))


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and returns structured JSON errors."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(
                "Unhandled exception on %s %s: %s",
                request.method,
                request.url.path,
                exc,
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": str(exc),
                    "path": str(request.url.path),
                    "timestamp": datetime.now(IST).isoformat(),
                },
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next):
        import time

        start = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000  # ms

        # Skip logging for health checks and WebSocket upgrades
        path = request.url.path
        if path not in ("/health", "/api/v1/health", "/ws"):
            logger.info(
                "%s %s → %d (%.0fms)",
                request.method,
                path,
                response.status_code,
                duration,
            )

        return response
