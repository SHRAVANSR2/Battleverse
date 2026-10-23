from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import IdMixin, TimestampMixin
from .enums import BattleStatus, BattleStyle, Intensity, PlaybackMode, enum_column
from app.core.db import Base

if TYPE_CHECKING:  # pragma: no cover
    from .character import Character
    from .verse import Verse
    from .vote import Vote


class Battle(IdMixin, TimestampMixin, Base):
    __tablename__ = "battles"
    __table_args__ = (
        sa.CheckConstraint("fighter_a_id <> fighter_b_id", name="ck_battles_distinct_fighters"),
        sa.CheckConstraint("round_count BETWEEN 1 AND 5", name="ck_battles_round_count"),
        sa.Index("ix_battles_status_created", "status", "created_at"),
        sa.Index("ix_battles_previous", "previous_battle_id"),
    )

    fighter_a_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("characters.id"), nullable=False
    )
    fighter_b_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("characters.id"), nullable=False
    )
    topic: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    style: Mapped[BattleStyle] = mapped_column(
        enum_column(BattleStyle, "battle_style"), nullable=False
    )
    intensity: Mapped[Intensity] = mapped_column(
        enum_column(Intensity, "battle_intensity"), nullable=False
    )
    round_count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    playback_mode: Mapped[PlaybackMode] = mapped_column(
        enum_column(PlaybackMode, "playback_mode"), nullable=False, default=PlaybackMode.MANUAL
    )
    status: Mapped[BattleStatus] = mapped_column(
        enum_column(BattleStatus, "battle_status"),
        nullable=False,
        default=BattleStatus.CREATED,
    )
    current_round: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    next_turn_number: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    state_version: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    previous_battle_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("battles.id"), nullable=True
    )
    winner_character_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("characters.id"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    fighter_a: Mapped["Character"] = relationship(foreign_keys=[fighter_a_id], lazy="joined")
    fighter_b: Mapped["Character"] = relationship(foreign_keys=[fighter_b_id], lazy="joined")
    winner: Mapped["Character | None"] = relationship(
        foreign_keys=[winner_character_id], lazy="joined"
    )
    verses: Mapped[list["Verse"]] = relationship(
        back_populates="battle",
        cascade="all, delete-orphan",
        order_by="Verse.turn_number",
    )
    votes: Mapped[list["Vote"]] = relationship(
        back_populates="battle", cascade="all, delete-orphan"
    )

    @property
    def total_turns(self) -> int:
        return self.round_count * 2

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Battle {self.id} {self.status.value} turn={self.next_turn_number}>"
