"""Fake TTS provider for tests and offline development.

It produces a **real, valid** 16-bit PCM WAV containing a soft tone whose length
tracks the text — not speech. It exists so API/audio/cache tests can run without
the Piper models. ``/api/health`` reports ``tts_provider: "fake"`` and the UI
shows a "synthetic test tone" chip, so it can never be mistaken for real speech.
"""

from __future__ import annotations

import io
import math
import struct
import wave

from .base import AudioResult, TTSProvider, Voice
from .voices import PIPER_VOICES

_SAMPLE_RATE = 22050


class FakeTTSProvider(TTSProvider):
    provider_name = "fake"

    def __init__(self, seconds_per_char: float = 0.012, max_seconds: float = 6.0) -> None:
        self._seconds_per_char = seconds_per_char
        self._max_seconds = max_seconds

    def list_voices(self) -> list[Voice]:
        return list(PIPER_VOICES)

    def voice_available(self, voice_id: str) -> bool:
        return any(voice.id == voice_id for voice in PIPER_VOICES)

    async def synthesize(self, text: str, voice_id: str) -> AudioResult:
        voice = next((v for v in PIPER_VOICES if v.id == voice_id), None)
        if voice is None:
            from app.core.errors import InvalidVoiceError

            raise InvalidVoiceError()

        seconds = max(0.35, min(self._max_seconds, len(text) * self._seconds_per_char))
        pitch = 320.0 if voice.gender == "female" else 180.0
        frames = int(_SAMPLE_RATE * seconds)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(_SAMPLE_RATE)
            samples = bytearray()
            for index in range(frames):
                envelope = min(1.0, index / 400, (frames - index) / 400)
                value = int(
                    5000
                    * envelope
                    * math.sin(2 * math.pi * pitch * index / _SAMPLE_RATE)
                )
                samples += struct.pack("<h", value)
            wav_file.writeframes(bytes(samples))

        data = buffer.getvalue()
        return AudioResult(
            data=data,
            content_type="audio/wav",
            sample_rate=_SAMPLE_RATE,
            duration_ms=int(seconds * 1000),
        )

    def health(self) -> tuple[bool, list[str]]:
        return True, []