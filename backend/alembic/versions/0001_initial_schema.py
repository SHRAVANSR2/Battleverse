"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

BATTLE_STYLE = sa.Enum(
    "rap", "roast", "debate",
    name="battle_style", native_enum=False, length=24,
    create_constraint=True,
)
INTENSITY = sa.Enum(
    "playful", "spicy", "fiery",
    name="battle_intensity", native_enum=False, length=24,
    create_constraint=True,
)
PLAYBACK_MODE = sa.Enum(
    "manual", "auto",
    name="playback_mode", native_enum=False, length=24,
    create_constraint=True,
)
BATTLE_STATUS = sa.Enum(
    "created", "in_progress", "awaiting_vote", "completed", "failed",
    name="battle_status", native_enum=False, length=24,
    create_constraint=True,
)
AUDIO_STATUS = sa.Enum(
    "pending", "ready", "failed",
    name="audio_status", native_enum=False, length=24,
    create_constraint=True,
)
MEMORY_TYPE = sa.Enum(
    "battle_result", "running_joke",
    name="memory_type", native_enum=False, length=24,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "characters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(48), nullable=False, unique=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("tagline", sa.String(160), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("personality", sa.JSON(), nullable=False),
        sa.Column("style_pref", sa.String(32), nullable=False, server_default="rap"),
        sa.Column("catchphrase", sa.String(160), nullable=False, server_default=""),
        sa.Column("voice_id", sa.String(64), nullable=False),
        sa.Column("accent", sa.String(16), nullable=False, server_default="mint"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "battles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "fighter_a_id", sa.String(36), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column(
            "fighter_b_id", sa.String(36), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column("topic", sa.String(120), nullable=False),
        sa.Column("style", BATTLE_STYLE, nullable=False),
        sa.Column("intensity", INTENSITY, nullable=False),
        sa.Column("round_count", sa.Integer(), nullable=False),
        sa.Column("playback_mode", PLAYBACK_MODE, nullable=False),
        sa.Column("status", BATTLE_STATUS, nullable=False),
        sa.Column("current_round", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_turn_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "previous_battle_id", sa.String(36), sa.ForeignKey("battles.id"), nullable=True
        ),
        sa.Column(
            "winner_character_id",
            sa.String(36),
            sa.ForeignKey("characters.id"),
            nullable=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "fighter_a_id <> fighter_b_id", name="ck_battles_distinct_fighters"
        ),
        sa.CheckConstraint("round_count BETWEEN 1 AND 5", name="ck_battles_round_count"),
    )
    op.create_index("ix_battles_status_created", "battles", ["status", "created_at"])
    op.create_index("ix_battles_previous", "battles", ["previous_battle_id"])

    op.create_table(
        "verses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "battle_id",
            sa.String(36),
            sa.ForeignKey("battles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("character_id", sa.String(36), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("verse_text", sa.Text(), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(80), nullable=False, server_default=""),
        sa.Column("provider", sa.String(24), nullable=False, server_default="demo"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("battle_id", "turn_number", name="uq_verses_battle_turn"),
    )
    op.create_index("ix_verses_battle_round", "verses", ["battle_id", "round_number"])

    op.create_table(
        "audio_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "verse_id",
            sa.String(36),
            sa.ForeignKey("verses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("voice_id", sa.String(64), nullable=False),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(160), nullable=True),
        sa.Column("content_type", sa.String(40), nullable=False, server_default="audio/wav"),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", AUDIO_STATUS, nullable=False),
        sa.Column("error_code", sa.String(48), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("verse_id", name="uq_audio_assets_verse"),
    )
    op.create_index("ix_audio_assets_cache_key", "audio_assets", ["cache_key"])
    op.create_index("ix_audio_assets_status", "audio_assets", ["status"])

    op.create_table(
        "votes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "battle_id",
            sa.String(36),
            sa.ForeignKey("battles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("voter_key", sa.String(64), nullable=False),
        sa.Column(
            "winner_character_id", sa.String(36), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("battle_id", "voter_key", name="uq_votes_battle_voter"),
    )

    op.create_table(
        "character_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "character_id",
            sa.String(36),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "related_battle_id",
            sa.String(36),
            sa.ForeignKey("battles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opponent_character_id", sa.String(36), sa.ForeignKey("characters.id"), nullable=False
        ),
        sa.Column("memory_type", MEMORY_TYPE, nullable=False),
        sa.Column("summary", sa.String(400), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "character_id", "related_battle_id", name="uq_memories_character_battle"
        ),
    )
    op.create_index("ix_memories_character", "character_memories", ["character_id", "created_at"])


def downgrade() -> None:
    op.drop_table("character_memories")
    op.drop_table("votes")
    op.drop_table("audio_assets")
    op.drop_table("verses")
    op.drop_table("battles")
    op.drop_table("characters")