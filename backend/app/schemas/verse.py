from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .common import ORMModel


class AudioOut(ORMModel):
    id: str
    verse_id: str
    provider: str
    voice_id: str
    url: str
    content_type: str
    size_bytes: int
    duration_ms: int
    status: str
    error_code: str | None = None
    cached: bool = False


class VerseOut(ORMModel):
    id: str
    battle_id: str
    character_id: str
    character_name: str = ""
    accent: str = ""
    round_number: int
    turn_number: int
    verse_text: str
    line_count: int
    model: str
    provider: str
    is_demo: bool = False
    created_at: datetime
    audio: AudioOut | None = None


class VerseTextOut(BaseModel):
    """Provider-independent shape returned by an LLM adapter."""

    verse_text: str
    line_count: int
    callback_reference: str = ""