from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .verse import VerseOut


class FighterResult(BaseModel):
    character_id: str
    name: str
    accent: str
    votes: int
    vote_share: float


class ResultOut(BaseModel):
    battle_id: str
    status: str
    is_draw: bool
    winner: FighterResult | None = None
    fighters: list[FighterResult]
    vote_count: int
    best_verse: VerseOut | None = None
    ai_judge: None = None
    decided_at: datetime | None = None