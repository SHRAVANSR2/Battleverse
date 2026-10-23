"""Enumerations stored as lowercase strings with CHECK constraints."""

from __future__ import annotations

from enum import Enum

import sqlalchemy as sa


class BattleStyle(str, Enum):
    RAP = "rap"
    ROAST = "roast"
    DEBATE = "debate"


class Intensity(str, Enum):
    PLAYFUL = "playful"
    SPICY = "spicy"
    FIERY = "fiery"


class PlaybackMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"


class BattleStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    AWAITING_VOTE = "awaiting_vote"
    COMPLETED = "completed"
    FAILED = "failed"


class AudioStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class MemoryType(str, Enum):
    BATTLE_RESULT = "battle_result"
    RUNNING_JOKE = "running_joke"


def enum_column(enum_cls: type[Enum], name: str, length: int = 24) -> sa.Enum:
    """VARCHAR + CHECK column storing enum *values* (not member names)."""
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda cls: [member.value for member in cls],
        length=length,
    )
