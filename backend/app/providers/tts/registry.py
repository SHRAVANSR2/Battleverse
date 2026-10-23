from __future__ import annotations

from app.core.config import Settings

from .base import TTSProvider
from .fake import FakeTTSProvider
from .piper_adapter import PiperTTSProvider


def build_tts_provider(settings: Settings) -> TTSProvider:
    if settings.tts_provider == "fake":
        return FakeTTSProvider()
    return PiperTTSProvider(
        voices_dir=settings.tts_voices_dir,
        timeout_seconds=settings.tts_timeout_seconds,
    )