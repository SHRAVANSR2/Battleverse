"""Real Piper synthesis — opt-in only.

Run with::

    python -m pytest backend/tests/real -m piper

Downloaded voice models are required (see docs/TTS.md). These tests are skipped
in the default run, which must stay network-free and piper-free.
"""

from __future__ import annotations

import io
import wave
from pathlib import Path

import pytest

from app.providers.tts.piper_adapter import PiperTTSProvider

pytestmark = pytest.mark.piper

VOICES_DIR = Path(__file__).resolve().parents[2] / "storage" / "models"

LINE = "I brought the thunder and a spare battery pack."


@pytest.fixture(scope="module")
def provider() -> PiperTTSProvider:
    candidate = PiperTTSProvider(VOICES_DIR, timeout_seconds=120)
    ready, missing = candidate.health()
    if not ready:
        pytest.skip(
            "Piper voice models missing: "
            + ", ".join(missing)
            + f". Download them into {VOICES_DIR} (see docs/TTS.md)."
        )
    return candidate


@pytest.mark.parametrize("voice_id", ["en_US-kristin-medium", "en_US-joe-medium"])
async def test_real_synthesis_produces_valid_wav(provider, voice_id):
    result = await provider.synthesize(LINE, voice_id)
    assert result.content_type == "audio/wav"
    assert len(result.data) > 10_000
    assert result.data[:4] == b"RIFF" and result.data[8:12] == b"WAVE"
    with wave.open(io.BytesIO(result.data), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 22_050
        seconds = wav_file.getnframes() / wav_file.getframerate()
    assert seconds > 1.0
    assert result.duration_ms == pytest.approx(seconds * 1000, rel=0.05)


async def test_the_two_voices_sound_different(provider):
    """Different speakers must not produce byte-identical audio."""
    a = await provider.synthesize(LINE, "en_US-kristin-medium")
    b = await provider.synthesize(LINE, "en_US-joe-medium")
    assert a.data != b.data
    assert a.sample_rate == b.sample_rate == 22_050
