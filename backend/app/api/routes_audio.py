from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse

from app.api.deps import SettingsDep, SessionDep, TTSDep
from app.schemas.verse import AudioOut
from app.services import audio_service

router = APIRouter(tags=["audio"])

_IMMUTABLE = "public, max-age=31536000, immutable"


def _storage(request: Request):
    return request.app.state.audio_storage


@router.post("/verses/{verse_id}/audio", response_model=AudioOut)
async def synthesize_verse_audio(
    verse_id: str,
    request: Request,
    session: SessionDep,
    tts: TTSDep,
    settings: SettingsDep,
) -> AudioOut:
    outcome = await audio_service.ensure_audio(
        session=session,
        verse_id=verse_id,
        tts=tts,
        storage=_storage(request),
        settings=settings,
    )
    asset = audio_service.get_asset(session, outcome.asset_id)
    return AudioOut(
        id=asset.id,
        verse_id=asset.verse_id,
        provider=asset.provider,
        voice_id=asset.voice_id,
        url=f"/api/audio/{asset.id}",
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        duration_ms=asset.duration_ms,
        status=asset.status.value,
        error_code=asset.error_code,
        cached=outcome.cached,
    )


@router.get("/audio/{audio_id}")
def serve_audio(audio_id: str, request: Request, session: SessionDep) -> Response:
    asset = audio_service.get_asset(session, audio_id)
    storage = _storage(request)
    path: Path = audio_service.resolve_audio_path(storage, asset)
    return FileResponse(
        path,
        media_type=asset.content_type or "audio/wav",
        filename=None,
        headers={
            "Cache-Control": _IMMUTABLE,
            "Accept-Ranges": "bytes",
            "X-Content-Type-Options": "nosniff",
        },
    )