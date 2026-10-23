"""Piper TTS adapter — real local neural speech.

``piper-tts`` is imported lazily so the app (and the test suite) runs without the
optional TTS extra installed. Voices are loaded on demand and cached; each voice
has its own lock because ``PiperVoice`` is not documented as thread-safe.
Synthesis runs in a worker thread so the event loop stays responsive.
"""

from __future__ import annotations

import asyncio
import io
import logging
import threading
import time
import wave
from pathlib import Path

from app.core.errors import TTSSynthesisError, TTSUnavailableError

from .base import AudioResult, TTSProvider, Voice
from .voices import PIPER_VOICES

logger = logging.getLogger(__name__)


class PiperTTSProvider(TTSProvider):
    provider_name = "piper"

    def __init__(self, voices_dir: Path, *, timeout_seconds: float = 60.0) -> None:
        self._voices_dir = Path(voices_dir)
        self._timeout = timeout_seconds
        self._voices: dict[str, Voice] = {voice.id: voice for voice in PIPER_VOICES}
        self._loaded: dict[str, object] = {}
        self._locks: dict[str, threading.Lock] = {
            voice_id: threading.Lock() for voice_id in self._voices
        }
        self._load_lock = threading.Lock()

    # --- provider API ---

    def list_voices(self) -> list[Voice]:
        return list(PIPER_VOICES)

    def voice_available(self, voice_id: str) -> bool:
        voice = self._voices.get(voice_id)
        if voice is None:
            return False
        model = self._voices_dir / voice.filename
        return model.is_file() and (self._voices_dir / f"{voice.filename}.json").is_file()

    def health(self) -> tuple[bool, list[str]]:
        missing = [vid for vid in self._voices if not self.voice_available(vid)]
        return (not missing), missing

    async def synthesize(self, text: str, voice_id: str) -> AudioResult:
        voice = self._voices.get(voice_id)
        if voice is None:
            raise TTSUnavailableError(f"Voice '{voice_id}' is not a known Piper voice.")
        if not self.voice_available(voice_id):
            raise TTSUnavailableError(
                f"Voice model '{voice.filename}' is missing from {self._voices_dir}. "
                "Download it with: python -m piper.download_voices "
                f"{voice_id} --download-dir backend\\storage\\models"
            )
        if not text.strip():
            raise TTSSynthesisError("There is no text to speak.")

        started = time.perf_counter()
        try:
            data, sample_rate = await asyncio.wait_for(
                asyncio.to_thread(self._synthesize_sync, text, voice), timeout=self._timeout
            )
        except TimeoutError as exc:
            raise TTSSynthesisError(
                "Speech generation timed out. The first run can be slow while the "
                "voice model loads — try again."
            ) from exc
        except (TTSUnavailableError, TTSSynthesisError):
            raise
        except Exception as exc:  # pragma: no cover - engine-specific failures
            logger.warning("Piper synthesis failed: %s", type(exc).__name__)
            raise TTSSynthesisError() from exc

        logger.info(
            "piper synthesized %d bytes in %.0f ms (voice=%s)",
            len(data),
            (time.perf_counter() - started) * 1000,
            voice_id,
        )
        return AudioResult(
            data=data,
            content_type="audio/wav",
            sample_rate=sample_rate,
            duration_ms=_duration_ms(data),
        )

    # --- internals ---

    def _load_voice(self, voice: Voice):
        cached = self._loaded.get(voice.id)
        if cached is not None:
            return cached
        with self._load_lock:
            cached = self._loaded.get(voice.id)
            if cached is not None:
                return cached
            try:
                from piper import PiperVoice
            except ImportError as exc:  # pragma: no cover - install guidance
                raise TTSUnavailableError(
                    "The 'piper-tts' package is not installed. "
                    'Run: pip install -e "backend[tts]"'
                ) from exc
            model_path = self._voices_dir / voice.filename
            loaded = PiperVoice.load(str(model_path))
            self._loaded[voice.id] = loaded
            logger.info("Loaded Piper voice %s", voice.id)
            return loaded

    def _synthesize_sync(self, text: str, voice: Voice) -> tuple[bytes, int]:
        piper_voice = self._load_voice(voice)
        lock = self._locks[voice.id]
        if not lock.acquire(timeout=self._timeout):
            raise TTSSynthesisError("That voice is busy speaking another line.")
        try:
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav_file:
                piper_voice.synthesize_wav(text, wav_file)
            data = buffer.getvalue()
        finally:
            lock.release()

        if len(data) < 44 or data[:4] != b"RIFF":
            raise TTSSynthesisError("The speech engine returned an invalid audio file.")
        with wave.open(io.BytesIO(data), "rb") as probe:
            sample_rate = probe.getframerate()
        return data, sample_rate


def _duration_ms(wav_bytes: bytes) -> int:
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate() or 1
            return int(frames * 1000 / rate)
    except Exception:  # pragma: no cover - defensive
        return 0