from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .common import ORMModel


class VoiceBrief(ORMModel):
    id: str
    label: str
    available: bool
    language: str = "en-US"
    gender: str | None = None


class CharacterOut(ORMModel):
    id: str
    slug: str
    name: str
    tagline: str
    description: str
    personality: dict[str, Any] = Field(default_factory=dict)
    style_pref: str
    catchphrase: str
    voice_id: str
    accent: str
    is_builtin: bool
    sort_order: int
    created_at: datetime