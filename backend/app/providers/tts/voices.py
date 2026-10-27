"""Allowlisted Piper voices.

Only voices with permissive dataset licences are used:

* ``en_US-kristin-medium`` — LibriVox (public domain), female
* ``en_US-joe-medium``     — CC0, male
* ``en_GB-alan-medium``    — LibriVox (public domain), British male
* ``en_US-amy-medium``     — CC0, female

Model files are downloaded by the user (see docs/TTS.md); they are never
committed. Unknown voice ids are rejected before touching the filesystem.
"""

from __future__ import annotations

from .base import Voice

PIPER_VOICES: tuple[Voice, ...] = (
    Voice(
        id="en_US-kristin-medium",
        label="Kristin (warm, female)",
        filename="en_US-kristin-medium.onnx",
        language="en-US",
        gender="female",
    ),
    Voice(
        id="en_US-joe-medium",
        label="Joe (dry, male)",
        filename="en_US-joe-medium.onnx",
        language="en-US",
        gender="male",
    ),
    Voice(
        id="en_GB-alan-medium",
        label="Alan (posh, British male)",
        filename="en_GB-alan-medium.onnx",
        language="en-GB",
        gender="male",
    ),
    Voice(
        id="en_US-amy-medium",
        label="Amy (bright, female)",
        filename="en_US-amy-medium.onnx",
        language="en-US",
        gender="female",
    ),
)

VOICE_IDS = {voice.id for voice in PIPER_VOICES}


def get_voice(voice_id: str) -> Voice | None:
    for voice in PIPER_VOICES:
        if voice.id == voice_id:
            return voice
    return None