from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import IdMixin, TimestampMixin
from .enums import AudioStatus, enum_column
from app.core.db import Base

if TYPE_CHECKING:  # pragma: no cover
    from .verse import Verse


class AudioAsset(IdMixin, TimestampMixin, Base):
    __tablename__ = "audio_assets"
    __table_args__ = (
        sa.UniqueConstraint("verse_id", name="uq_audio_assets_verse"),
        sa.Index("ix_audio_assets_cache_key", "cache_key"),
        sa.Index("ix_audio_assets_status", "status"),
    )

    verse_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("verses.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(sa.String(24), nullable=False)
    voice_id: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    cache_key: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(sa.String(160), nullable=True)
    content_type: Mapped[str] = mapped_column(
        sa.String(40), nullable=False, default="audio/wav"
    )
    size_bytes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    status: Mapped[AudioStatus] = mapped_column(
        enum_column(AudioStatus, "audio_status"), nullable=False, default=AudioStatus.PENDING
    )
    error_code: Mapped[str | None] = mapped_column(sa.String(48), nullable=True)

    verse: Mapped["Verse"] = relationship(back_populates="audio")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<AudioAsset verse={self.verse_id} {self.status.value}>"
