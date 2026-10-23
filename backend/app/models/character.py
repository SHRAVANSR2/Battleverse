from __future__ import annotations

from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import IdMixin, TimestampMixin
from app.core.db import Base

if TYPE_CHECKING:  # pragma: no cover
    from .memory import CharacterMemory


class Character(IdMixin, TimestampMixin, Base):
    __tablename__ = "characters"

    slug: Mapped[str] = mapped_column(sa.String(48), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(sa.String(60), nullable=False)
    tagline: Mapped[str] = mapped_column(sa.String(160), nullable=False, default="")
    description: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")
    personality: Mapped[dict[str, Any]] = mapped_column(sa.JSON, nullable=False, default=dict)
    style_pref: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="rap")
    catchphrase: Mapped[str] = mapped_column(sa.String(160), nullable=False, default="")
    voice_id: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    accent: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="mint")
    is_builtin: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    memories: Mapped[list["CharacterMemory"]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
        foreign_keys="CharacterMemory.character_id",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Character {self.slug}>"
