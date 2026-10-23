"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import (
    routes_audio,
    routes_battles,
    routes_characters,
    routes_health,
    routes_history,
    routes_tts,
    routes_votes,
)
from app.core.config import Settings, get_settings
from app.core.db import create_db_engine, create_session_factory
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.request_context import get_request_id, new_request_id, set_request_id

logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or new_request_id()
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="BattleVerse API",
        version=settings.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    engine = create_db_engine(settings.database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.llm = None
    app.state.tts = None
    settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
    from app.services.audio_storage import AudioStorage

    app.state.audio_storage = AudioStorage(settings.audio_storage_dir)

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id", "content-range", "accept-ranges"],
    )

    @app.exception_handler(AppError)
    async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_envelope(get_request_id()),
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 404:
            code, message = "NOT_FOUND", "We could not find that."
        elif exc.status_code == 405:
            code, message = "METHOD_NOT_ALLOWED", "That method is not supported here."
        else:
            code = "HTTP_ERROR"
            message = str(exc.detail) if exc.detail else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {"code": code, "message": message, "request_id": get_request_id()}
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ())[1:]),
                "message": error.get("msg", "Invalid value"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": details[0]["message"] if details else "Invalid request.",
                    "request_id": get_request_id(),
                    "details": {"fields": details},
                }
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Something went wrong on our side.",
                    "request_id": get_request_id(),
                }
            },
        )

    for module in (
        routes_health,
        routes_characters,
        routes_battles,
        routes_votes,
        routes_history,
        routes_tts,
        routes_audio,
    ):
        app.include_router(module.router, prefix="/api")

    if settings.demo_mode:
        logger.info("LLM provider: demo (GROQ_API_KEY not set — verses are scripted).")
    else:
        logger.info("LLM provider: groq (model=%s).", settings.llm_model)

    return app


app = create_app()