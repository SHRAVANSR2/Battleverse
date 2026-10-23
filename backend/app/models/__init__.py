"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from app.core.db import Base

from .audio_asset import AudioAsset
from .battle import Battle
from .character import Character
from .enums import (
    AudioStatus,
    BattleStatus,
    BattleStyle,
    Intensity,
    MemoryType,
    PlaybackMode,
)
from .memory import CharacterMemory
from .verse import Verse
from .vote import Vote

__all__ = [
    "AudioAsset",
    "AudioStatus",
    "Base",
    "Battle",
    "BattleStatus",
    "BattleStyle",
    "Character",
    "CharacterMemory",
    "Intensity",
    "MemoryType",
    "PlaybackMode",
    "Verse",
    "Vote",
]
