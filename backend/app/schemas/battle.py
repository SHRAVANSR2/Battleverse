from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from .character import CharacterOut
from .result import FighterResult, ResultOut
from .verse import VerseOut


class CreateBattleIn(BaseModel):
    fighter_a_id: str
    fighter_b_id: str
    topic: str = Field(min_length=3, max_length=120)
    style: str = "rap"
    intensity: str = "playful"
    round_count: int = Field(default=3, ge=1, le=5)
    playback_mode: str = "manual"

    @field_validator("topic")
    @classmethod
    def _clean_topic(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 3:
            raise ValueError("Give the battle a topic of at least 3 characters.")
        return cleaned

    @field_validator("style")
    @classmethod
    def _valid_style(cls, value: str) -> str:
        if value not in {"rap", "roast", "debate"}:
            raise ValueError("style must be rap, roast or debate")
        return value

    @field_validator("intensity")
    @classmethod
    def _valid_intensity(cls, value: str) -> str:
        if value not in {"playful", "spicy", "fiery"}:
            raise ValueError("intensity must be playful, spicy or fiery")
        return value

    @field_validator("playback_mode")
    @classmethod
    def _valid_playback(cls, value: str) -> str:
        if value not in {"manual", "auto"}:
            raise ValueError("playback_mode must be manual or auto")
        return value

    @model_validator(mode="after")
    def _distinct_fighters(self) -> "CreateBattleIn":
        if self.fighter_a_id == self.fighter_b_id:
            raise ValueError("Pick two different robots.")
        return self


class TurnRequestIn(BaseModel):
    expected_turn_number: int | None = Field(default=None, ge=1, le=10)
    idempotency_key: str | None = Field(default=None, max_length=64)


class BattleOut(BaseModel):
    id: str
    topic: str
    style: str
    intensity: str
    round_count: int
    playback_mode: str
    status: str
    current_round: int
    next_turn_number: int
    total_turns: int
    state_version: int
    previous_battle_id: str | None = None
    winner_character_id: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class BattleSummaryOut(BattleOut):
    fighter_a_name: str
    fighter_b_name: str
    fighter_a_accent: str
    fighter_b_accent: str
    fighter_a_slug: str
    fighter_b_slug: str
    verse_count: int = 0
    winner_name: str | None = None
    rival_note: str | None = None


class BattleDetailOut(BattleOut):
    fighter_a: CharacterOut
    fighter_b: CharacterOut
    verses: list[VerseOut] = Field(default_factory=list)
    result: "ResultOut | None" = None


class TurnOut(BaseModel):
    battle: BattleOut
    verse: VerseOut
    created: bool


class VoteIn(BaseModel):
    winner_character_id: str
    voter_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class VoteOut(BaseModel):
    vote_id: str
    battle_id: str
    winner_character_id: str
    created: bool


class VoteResponseOut(BaseModel):
    vote: VoteOut
    battle: BattleOut
    result: ResultOut


class LeaderboardRowOut(BaseModel):
    character_id: str
    slug: str
    name: str
    accent: str
    battles: int
    wins: int
    losses: int
    win_rate: float
    last_battle_at: datetime | None = None