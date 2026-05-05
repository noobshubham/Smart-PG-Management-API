"""Centralised error handling.

A single `register_exception_handlers(app)` install:
- Logs the full traceback with the request_id from middleware.
- Returns a sanitised JSON body so internal details don't leak.

Domain exceptions are still handled at the router layer (where they map to
the right HTTP status). This is the catch-all for anything unhandled.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.integrations.ai.base import AIUnavailableError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AIUnavailableError)
    async def _ai_unavailable(request: Request, exc: AIUnavailableError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning("AI provider unavailable request_id=%s path=%s detail=%s",
                       request_id, request.url.path, exc)
        return JSONResponse(
            status_code=503,
            content={
                "detail": f"AI provider unavailable: {exc}",
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception("unhandled error request_id=%s path=%s",
                         request_id, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
            },
        )
