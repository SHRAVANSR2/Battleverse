from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import IdMixin, TimestampMixin
from app.core.db import Base

if TYPE_CHECKING:  # pragma: no cover
    from .audio_asset import AudioAsset
    from .battle import Battle
    from .character import Character


class Verse(IdMixin, TimestampMixin, Base):
    __tablename__ = "verses"
    __table_args__ = (
        sa.UniqueConstraint("battle_id", "turn_number", name="uq_verses_battle_turn"),
        sa.Index("ix_verses_battle_round", "battle_id", "round_number"),
    )

    battle_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("battles.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("characters.id"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    turn_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    verse_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    line_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    model: Mapped[str] = mapped_column(sa.String(80), nullable=False, default="")
    provider: Mapped[str] = mapped_column(sa.String(24), nullable=False, default="demo")

    battle: Mapped["Battle"] = relationship(back_populates="verses")
    character: Mapped["Character"] = relationship(lazy="joined")
    audio: Mapped["AudioAsset | None"] = relationship(
        back_populates="verse", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Verse battle={self.battle_id} turn={self.turn_number}>"
