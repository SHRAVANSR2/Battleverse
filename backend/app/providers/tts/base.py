"""TTS provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Voice:
    id: str
    label: str
    filename: str
    language: str = "en-US"
    gender: str | None = None


@dataclass(frozen=True)
class AudioResult:
    data: bytes
    content_type: str = "audio/wav"
    sample_rate: int = 22050
    duration_ms: int = 0


class TTSProvider(ABC):
    provider_name = "unknown"

    @abstractmethod
    def list_voices(self) -> list[Voice]:
        """Declared voices. Must not load models."""

    @abstractmethod
    def voice_available(self, voice_id: str) -> bool:
        """Whether the model file for this voice exists."""

    @abstractmethod
    async def synthesize(self, text: str, voice_id: str) -> AudioResult:
        """Render speech. Raises AppError subclasses on failure."""

    @abstractmethod
    def health(self) -> tuple[bool, list[str]]:
        """(ready, missing voice ids). Must not load models."""

    def voices(self) -> dict[str, Voice]:
        return {voice.id: voice for voice in self.list_voices()}