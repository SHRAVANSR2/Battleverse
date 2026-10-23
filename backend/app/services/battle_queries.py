"""Load battles and shape them into API DTOs."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BattleNotFoundError, CharacterNotFoundError
from app.models import Battle, Character, Verse
from app.schemas.battle import BattleOut, BattleSummaryOut
from app.schemas.character import CharacterOut
from app.schemas.result import ResultOut
from app.schemas.verse import AudioOut, VerseOut


def get_battle(session: Session, battle_id: str) -> Battle:
    battle = session.get(Battle, battle_id)
    if battle is None:
        raise BattleNotFoundError()
    return battle


def get_character(session: Session, character_id: str) -> Character:
    character = session.get(Character, character_id)
    if character is None:
        raise CharacterNotFoundError()
    return character


def battle_out(battle: Battle) -> BattleOut:
    return BattleOut(
        id=battle.id,
        topic=battle.topic,
        style=battle.style.value,
        intensity=battle.intensity.value,
        round_count=battle.round_count,
        playback_mode=battle.playback_mode.value,
        status=battle.status.value,
        current_round=battle.current_round,
        next_turn_number=battle.next_turn_number,
        total_turns=battle.total_turns,
        state_version=battle.state_version,
        previous_battle_id=battle.previous_battle_id,
        winner_character_id=battle.winner_character_id,
        created_at=battle.created_at,
        completed_at=battle.completed_at,
    )


def character_out(character: Character) -> CharacterOut:
    return CharacterOut.model_validate(character)


def verse_out(verse: Verse) -> VerseOut:
    asset = verse.audio
    audio = None
    if asset is not None and asset.status.value == "ready" and asset.storage_key:
        audio = AudioOut(
            id=asset.id,
            verse_id=asset.verse_id,
            provider=asset.provider,
            voice_id=asset.voice_id,
            url=f"/api/audio/{asset.id}",
            content_type=asset.content_type,
            size_bytes=asset.size_bytes,
            duration_ms=asset.duration_ms,
            status=asset.status.value,
            error_code=asset.error_code,
        )
    return VerseOut(
        id=verse.id,
        battle_id=verse.battle_id,
        character_id=verse.character_id,
        character_name=verse.character.name,
        accent=verse.character.accent,
        round_number=verse.round_number,
        turn_number=verse.turn_number,
        verse_text=verse.verse_text,
        line_count=verse.line_count,
        model=verse.model,
        provider=verse.provider,
        is_demo=verse.provider == "demo",
        created_at=verse.created_at,
        audio=audio,
    )


def load_verses(session: Session, battle_id: str) -> list[Verse]:
    stmt = (
        select(Verse)
        .where(Verse.battle_id == battle_id)
        .order_by(Verse.turn_number)
        .options(selectinload(Verse.audio))
    )
    return list(session.scalars(stmt).unique())


def latest_verses(session: Session, battle_id: str, limit: int = 3) -> list[Verse]:
    stmt = (
        select(Verse)
        .where(Verse.battle_id == battle_id)
        .order_by(Verse.turn_number.desc())
        .limit(limit)
    )
    recent = list(session.scalars(stmt))
    return list(reversed(recent))


def verse_by_turn(session: Session, battle_id: str, turn_number: int) -> Verse | None:
    stmt = select(Verse).where(
        Verse.battle_id == battle_id, Verse.turn_number == turn_number
    )
    return session.scalars(stmt).first()


def battle_summary(
    session: Session,
    battle: Battle,
    *,
    verse_count: int | None = None,
    rival_note: str | None = None,
) -> BattleSummaryOut:
    if verse_count is None:
        verse_count = int(
            session.scalar(
                select(func.count(Verse.id)).where(Verse.battle_id == battle.id)
            )
            or 0
        )
    winner_name = battle.winner.name if battle.winner is not None else None
    return BattleSummaryOut(
        **battle_out(battle).model_dump(),
        fighter_a_name=battle.fighter_a.name,
        fighter_b_name=battle.fighter_b.name,
        fighter_a_accent=battle.fighter_a.accent,
        fighter_b_accent=battle.fighter_b.accent,
        fighter_a_slug=battle.fighter_a.slug,
        fighter_b_slug=battle.fighter_b.slug,
        verse_count=verse_count,
        winner_name=winner_name,
        rival_note=rival_note,
    )


def battle_detail(
    session: Session,
    battle: Battle,
    *,
    result: ResultOut | None = None,
) -> dict:
    verses = load_verses(session, battle.id)
    return {
        **battle_out(battle).model_dump(),
        "fighter_a": character_out(battle.fighter_a).model_dump(),
        "fighter_b": character_out(battle.fighter_b).model_dump(),
        "verses": [verse_out(verse).model_dump() for verse in verses],
        "result": result.model_dump() if result is not None else None,
    }