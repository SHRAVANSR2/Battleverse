from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import IdMixin, TimestampMixin
from app.core.db import Base

if TYPE_CHECKING:  # pragma: no cover
    from .battle import Battle


class Vote(IdMixin, TimestampMixin, Base):
    __tablename__ = "votes"
    __table_args__ = (
        sa.UniqueConstraint("battle_id", "voter_key", name="uq_votes_battle_voter"),
    )

    battle_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("battles.id", ondelete="CASCADE"), nullable=False
    )
    voter_key: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    winner_character_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("characters.id"), nullable=False
    )

    battle: Mapped["Battle"] = relationship(back_populates="votes")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Vote battle={self.battle_id} winner={self.winner_character_id}>"
