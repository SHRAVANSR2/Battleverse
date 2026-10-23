"""Vote tallies and result payloads."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Battle, Character, Verse, Vote
from app.schemas.result import FighterResult, ResultOut
from app.services.battle_queries import verse_out


def vote_counts(session: Session, battle_id: str) -> dict[str, int]:
    stmt = (
        select(Vote.winner_character_id, func.count(Vote.id))
        .where(Vote.battle_id == battle_id)
        .group_by(Vote.winner_character_id)
    )
    return {row[0]: int(row[1]) for row in session.execute(stmt)}


def best_verse(session: Session, battle: Battle, winner_id: str | None) -> Verse | None:
    """The winner's last verse is the one users hear last; use it as the highlight."""
    stmt = (
        select(Verse)
        .where(Verse.battle_id == battle.id)
        .order_by(Verse.turn_number.desc())
        .limit(1)
    )
    fallback = session.scalars(stmt).first()
    if winner_id is None:
        return fallback
    stmt = (
        select(Verse)
        .where(Verse.battle_id == battle.id, Verse.character_id == winner_id)
        .order_by(Verse.turn_number.desc())
        .limit(1)
    )
    return session.scalars(stmt).first() or fallback


def build_result(session: Session, battle: Battle) -> ResultOut:
    counts = vote_counts(session, battle.id)
    total = sum(counts.values())

    fighters: list[FighterResult] = []
    for fighter in (battle.fighter_a, battle.fighter_b):
        votes = counts.get(fighter.id, 0)
        fighters.append(
            FighterResult(
                character_id=fighter.id,
                name=fighter.name,
                accent=fighter.accent,
                votes=votes,
                vote_share=round(votes / total, 4) if total else 0.0,
            )
        )

    winner_fighter = next(
        (f for f in fighters if f.character_id == battle.winner_character_id), None
    )
    is_draw = battle.winner_character_id is None and battle.status.value == "completed"
    highlight = best_verse(session, battle, battle.winner_character_id)

    return ResultOut(
        battle_id=battle.id,
        status=battle.status.value,
        is_draw=is_draw,
        winner=winner_fighter,
        fighters=fighters,
        vote_count=total,
        best_verse=verse_out(highlight) if highlight is not None else None,
        ai_judge=None,
        decided_at=battle.completed_at,
    )


def leaderboard(session: Session) -> list[dict]:
    characters = list(
        session.scalars(select(Character).where(Character.is_builtin.is_(True)))
    )
    rows = []
    for character in characters:
        battles = list(
            session.scalars(
                select(Battle).where(
                    Battle.status == "completed",
                )
            )
        )
        involved = [
            b for b in battles if character.id in (b.fighter_a_id, b.fighter_b_id)
        ]
        wins = sum(1 for b in involved if b.winner_character_id == character.id)
        last = max((b.completed_at for b in involved if b.completed_at), default=None)
        rows.append(
            {
                "character_id": character.id,
                "slug": character.slug,
                "name": character.name,
                "accent": character.accent,
                "battles": len(involved),
                "wins": wins,
                "losses": len(involved) - wins,
                "win_rate": round(wins / len(involved), 4) if involved else 0.0,
                "last_battle_at": last,
            }
        )
    rows.sort(key=lambda row: (-row["win_rate"], -row["wins"], row["name"]))
    return rows