"""Verse-audio orchestration: cache key, synthesis, persistence.

Guarantees:
* synthesis never runs inside a database transaction;
* an identical (provider, voice, settings, text) reuses the stored file;
* a synthesis failure stores ``status=failed`` and leaves the verse untouched;
* the client only ever sees ``/api/audio/{audio_id}``, never a file path.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import (
    AudioFileMissingError,
    AudioNotFoundError,
    InvalidVoiceError,
    TTSSynthesisError,
)
from app.models import AudioAsset, AudioStatus, Verse
from app.providers.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_CACHE_VERSION = "v1"
_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().lower()


def build_cache_key(provider: str, voice_id: str, settings_json: str, text: str) -> str:
    payload = "\x1f".join(
        (_CACHE_VERSION, provider, voice_id, settings_json, normalize_text(text))
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def settings_signature(settings: Settings) -> str:
    """Only settings that change the rendered audio belong here."""
    return f"rate={settings.tts_max_text_chars}"


@dataclass(frozen=True)
class AudioOutcome:
    asset_id: str
    created: bool
    cached: bool


def get_verse_or_404(session: Session, verse_id: str) -> Verse:
    from app.core.errors import VerseNotFoundError

    verse = session.get(Verse, verse_id)
    if verse is None:
        raise VerseNotFoundError()
    return verse


def get_asset(session: Session, audio_id: str) -> AudioAsset:
    asset = session.get(AudioAsset, audio_id)
    if asset is None:
        raise AudioNotFoundError()
    return asset


async def ensure_audio(
    *,
    session: Session,
    verse_id: str,
    tts: TTSProvider,
    storage,
    settings: Settings,
    force: bool = False,
) -> AudioOutcome:
    verse = get_verse_or_404(session, verse_id)
    voice_id = verse.character.voice_id

    if not any(voice.id == voice_id for voice in tts.list_voices()):
        raise InvalidVoiceError(f"The voice '{voice_id}' is not configured.")

    if len(verse.verse_text) > settings.tts_max_text_chars:
        raise TTSSynthesisError(
            f"That verse is too long to speak (limit {settings.tts_max_text_chars} characters)."
        )

    cache_key = build_cache_key(
        tts.provider_name, voice_id, settings_signature(settings), verse.verse_text
    )

    # --- existing row for this verse ---------------------------------------
    asset = session.scalars(
        select(AudioAsset).where(AudioAsset.verse_id == verse.id)
    ).first()

    if not force and asset is not None and asset.status == AudioStatus.READY and asset.storage_key:
        if storage.exists(asset.storage_key) and asset.cache_key == cache_key:
            return AudioOutcome(asset.id, created=False, cached=True)

    # --- identical audio already on disk (another verse) --------------------
    if not force:
        twin = session.scalars(
            select(AudioAsset).where(
                AudioAsset.cache_key == cache_key,
                AudioAsset.status == AudioStatus.READY,
                AudioAsset.storage_key.is_not(None),
            )
        ).first()
        if twin is not None and storage.exists(twin.storage_key or ""):
            _upsert_asset(
                session,
                verse=verse,
                provider=tts.provider_name,
                voice_id=voice_id,
                cache_key=cache_key,
                storage_key=twin.storage_key,
                size_bytes=twin.size_bytes,
                duration_ms=twin.duration_ms,
                status=AudioStatus.READY,
            )
            session.commit()
            return AudioOutcome(_asset_id(session, verse.id), created=True, cached=True)

    # --- synthesize (no transaction held open by us) ------------------------
    try:
        result = await tts.synthesize(verse.verse_text, voice_id)
    except Exception as exc:
        code = getattr(exc, "code", "TTS_SYNTHESIS_FAILED")
        _record_failure(session, verse, tts.provider_name, voice_id, cache_key, code)
        session.commit()
        raise

    storage_key, size_bytes = storage.write(result.data)
    _upsert_asset(
        session,
        verse=verse,
        provider=tts.provider_name,
        voice_id=voice_id,
        cache_key=cache_key,
        storage_key=storage_key,
        size_bytes=size_bytes,
        duration_ms=result.duration_ms,
        status=AudioStatus.READY,
    )
    session.commit()
    return AudioOutcome(_asset_id(session, verse.id), created=True, cached=False)


def _asset_id(session: Session, verse_id: str) -> str:
    asset = session.scalars(
        select(AudioAsset).where(AudioAsset.verse_id == verse_id)
    ).first()
    if asset is None:  # pragma: no cover - defensive
        raise AudioNotFoundError()
    return asset.id


def _upsert_asset(
    session: Session,
    *,
    verse: Verse,
    provider: str,
    voice_id: str,
    cache_key: str,
    storage_key: str | None,
    size_bytes: int,
    duration_ms: int,
    status: AudioStatus,
    error_code: str | None = None,
) -> AudioAsset:
    asset = session.scalars(
        select(AudioAsset).where(AudioAsset.verse_id == verse.id)
    ).first()
    if asset is None:
        asset = AudioAsset(
            verse_id=verse.id,
            provider=provider,
            voice_id=voice_id,
            cache_key=cache_key,
            storage_key=storage_key,
            content_type="audio/wav",
            size_bytes=size_bytes,
            duration_ms=duration_ms,
            status=status,
            error_code=error_code,
        )
        session.add(asset)
    else:
        asset.provider = provider
        asset.voice_id = voice_id
        asset.cache_key = cache_key
        asset.storage_key = storage_key
        asset.size_bytes = size_bytes
        asset.duration_ms = duration_ms
        asset.status = status
        asset.error_code = error_code
    session.flush()
    return asset


def _record_failure(
    session: Session,
    verse: Verse,
    provider: str,
    voice_id: str,
    cache_key: str,
    error_code: str,
) -> None:
    existing = session.scalars(
        select(AudioAsset).where(AudioAsset.verse_id == verse.id)
    ).first()
    # Never clobber a good file with a failure row.
    if existing is not None and existing.status == AudioStatus.READY:
        return
    _upsert_asset(
        session,
        verse=verse,
        provider=provider,
        voice_id=voice_id,
        cache_key=cache_key,
        storage_key=None,
        size_bytes=0,
        duration_ms=0,
        status=AudioStatus.FAILED,
        error_code=error_code,
    )


def resolve_audio_path(storage, asset: AudioAsset):
    if not asset.storage_key:
        raise AudioNotFoundError()
    if not storage.exists(asset.storage_key):
        raise AudioFileMissingError()
    return storage.resolve(asset.storage_key)