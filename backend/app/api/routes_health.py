from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import inspect

from app.schemas.common import HealthOut

router = APIRouter(tags=["health"])

_TABLES = ("characters", "battles", "verses", "audio_assets", "votes", "character_memories")


@router.get("/health", response_model=HealthOut)
def health(request: Request) -> HealthOut:
    settings = request.app.state.settings
    engine = request.app.state.engine

    database_ready = False
    try:
        existing = set(inspect(engine).get_table_names())
        database_ready = all(table in existing for table in _TABLES)
    except Exception:  # pragma: no cover - engine missing/unreachable
        database_ready = False

    tts = getattr(request.app.state, "tts", None)
    if tts is None:
        from app.providers.tts.registry import build_tts_provider

        tts = build_tts_provider(settings)
        request.app.state.tts = tts

    voices = tts.list_voices()
    tts_ready, _missing = tts.health()
    return HealthOut(
        status="ok" if database_ready else "degraded",
        version=settings.app_version,
        database_ready=database_ready,
        llm_provider=settings.llm_provider_name,
        llm_model=settings.llm_model,
        llm_key_present=settings.has_llm_key,
        demo_mode=settings.demo_mode,
        tts_provider=tts.provider_name,
        tts_voices=len(voices),
        tts_ready=tts_ready,
    )