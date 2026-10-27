"""Compact rivalry memory.

After a battle is decided we write one short summary per fighter. Future prompts
for the same pair inject at most two of these, keeping prompts small.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Battle, CharacterMemory, MemoryType


def record_result_memories(session: Session, battle: Battle) -> None:
    if battle.winner_character_id is None:
        return  # draws are not memorable enough to persist

    # `battle.winner` is a lazy-joined relationship that was loaded BEFORE
    # winner_character_id got set, so it is still None here — resolve through
    # the always-loaded fighters instead.
    winner = (
        battle.fighter_a
        if battle.winner_character_id == battle.fighter_a_id
        else battle.fighter_b
    )
    loser = battle.fighter_b if winner is battle.fighter_a else battle.fighter_a

    # Deliberately NO topic: old topics leak into every future prompt and the
    # robots start roasting "Coding at midnight" in an antenna battle.
    for character_id, opponent_id, summary in (
        (
            winner.id,
            loser.id,
            f"Beat {loser.name} in a {battle.round_count}-round {battle.style.value} battle.",
        ),
        (
            loser.id,
            winner.id,
            f"Lost to {winner.name} in a {battle.round_count}-round {battle.style.value} battle.",
        ),
    ):
        _upsert(session, character_id, opponent_id, battle.id, summary)


def _upsert(
    session: Session,
    character_id: str,
    opponent_id: str,
    battle_id: str,
    summary: str,
) -> None:
    existing = session.scalars(
        select(CharacterMemory).where(
            CharacterMemory.character_id == character_id,
            CharacterMemory.related_battle_id == battle_id,
        )
    ).first()
    if existing is not None:
        existing.summary = summary[:400]
        return
    session.add(
        CharacterMemory(
            character_id=character_id,
            related_battle_id=battle_id,
            opponent_character_id=opponent_id,
            memory_type=MemoryType.BATTLE_RESULT,
            summary=summary[:400],
            importance=1,
        )
    )
    session.flush()


def memories_for(
    session: Session,
    character_id: str,
    opponent_id: str,
    *,
    limit: int = 2,
) -> list[CharacterMemory]:
    stmt = (
        select(CharacterMemory)
        .where(
            CharacterMemory.character_id == character_id,
            CharacterMemory.opponent_character_id == opponent_id,
        )
        .order_by(CharacterMemory.created_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def rival_note(session: Session, battle: Battle) -> str | None:
    """A one-line reminder shown in history ("Last time Nova Vex won")."""
    previous_id = battle.previous_battle_id
    if not previous_id:
        return None
    previous = session.get(Battle, previous_id)
    if previous is None or previous.winner is None:
        return None
    return f"Last time {previous.winner.name} won."