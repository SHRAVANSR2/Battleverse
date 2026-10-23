from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import SessionDep, SettingsDep, TTSDep
from app.core.errors import InvalidVoiceError
from app.models import Character
from app.schemas.common import TTSHealthOut, VoiceOut

router = APIRouter(prefix="/tts", tags=["tts"])


class PreviewIn(BaseModel):
    voice_id: str
    text: str = Field(min_length=1, max_length=200)


@router.get("/voices", response_model=list[VoiceOut])
def list_voices(session: SessionDep, tts: TTSDep) -> list[VoiceOut]:
    characters = list(session.scalars(select(Character)))
    by_voice: dict[str, list[str]] = {}
    for character in characters:
        by_voice.setdefault(character.voice_id, []).append(character.name)

    return [
        VoiceOut(
            id=voice.id,
            label=voice.label,
            available=tts.voice_available(voice.id),
            characters_using=by_voice.get(voice.id, []),
            sample_text=f"Hi, I'm one of the BattleVerse robots. {voice.label}.",
            language=voice.language,
            gender=voice.gender,
        )
        for voice in tts.list_voices()
    ]


@router.get("/health", response_model=TTSHealthOut)
def tts_health(settings: SettingsDep, tts: TTSDep) -> TTSHealthOut:
    ready, missing = tts.health()
    return TTSHealthOut(
        provider=tts.provider_name,
        available=ready,
        voices_found=len(tts.list_voices()) - len(missing),
        missing_models=missing,
        voices_dir=str(settings.tts_voices_dir),
    )


@router.post("/preview")
async def preview_voice(
    payload: PreviewIn,
    request: Request,
    tts: TTSDep,
) -> Response:
    voices = {voice.id for voice in tts.list_voices()}
    if payload.voice_id not in voices:
        raise InvalidVoiceError()
    result = await tts.synthesize(payload.text, payload.voice_id)
    return Response(
        content=result.data,
        media_type=result.content_type,
        headers={"Cache-Control": "no-store"},
    )