from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import IdMixin, TimestampMixin
from .enums import MemoryType, enum_column
from app.core.db import Base

if TYPE_CHECKING:  # pragma: no cover
    from .character import Character


class CharacterMemory(IdMixin, TimestampMixin, Base):
    """Compact rivalry memory injected into future prompts."""

    __tablename__ = "character_memories"
    __table_args__ = (
        sa.UniqueConstraint(
            "character_id", "related_battle_id", name="uq_memories_character_battle"
        ),
        sa.Index("ix_memories_character", "character_id", "created_at"),
    )

    character_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    related_battle_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("battles.id", ondelete="CASCADE"), nullable=False
    )
    opponent_character_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("characters.id"), nullable=False
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        enum_column(MemoryType, "memory_type"), nullable=False
    )
    summary: Mapped[str] = mapped_column(sa.String(400), nullable=False)
    importance: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)

    character: Mapped["Character"] = relationship(
        back_populates="memories", foreign_keys=[character_id]
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<CharacterMemory character={self.character_id} battle={self.related_battle_id}>"
