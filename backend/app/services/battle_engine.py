"""Battle orchestration: create, generate a turn, vote, rematch.

Correctness rules (each has a dedicated test):

1. The turn pointer only advances after the verse is persisted.
2. The LLM call happens **outside** any open transaction.
3. The write is a compare-and-swap on ``(state_version, next_turn_number)``.
4. ``UNIQUE(battle_id, turn_number)`` is the final guard.
5. An idempotent replay of an already-generated turn returns the stored verse
   with ``created: false`` instead of calling the provider again.
6. Provider failures leave the battle untouched.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import (
    BattleNotInProgressError,
    BattleNotVotableError,
    TurnBusyError,
    ProviderInvalidOutputError,
    TurnConflictError,
    ValidationFailedError,
)
from app.models import (
    Battle,
    BattleStatus,
    BattleStyle,
    Character,
    Intensity,
    PlaybackMode,
    Verse,
)
from app.providers.llm.base import LLMProvider, VerseRequest
from app.providers.llm.registry import LLMProviderPair
from app.schemas.battle import CreateBattleIn
from app.services import turn_math
from app.services.battle_queries import (
    battle_detail,
    battle_out,
    character_out,
    get_battle,
    get_character,
    latest_verses,
    verse_by_turn,
    verse_out,
)
from app.services.locks import battle_lock
from app.services.memory import record_result_memories
from app.services.prompt_builder import build_prompt, echo_terms, topic_terms
from app.services.results import build_result
from app.services.verse_validator import numbers_in, parse_verse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TurnResult:
    """Serialized while the session is open — never holds detached ORM objects."""

    battle_payload: dict
    verse_payload: dict
    created: bool


# ---------------------------------------------------------------- create


def create_battle(session: Session, payload: CreateBattleIn) -> Battle:
    fighter_a = get_character(session, payload.fighter_a_id)
    fighter_b = get_character(session, payload.fighter_b_id)

    battle = Battle(
        fighter_a_id=fighter_a.id,
        fighter_b_id=fighter_b.id,
        topic=payload.topic,
        style=BattleStyle(payload.style),
        intensity=Intensity(payload.intensity),
        round_count=payload.round_count,
        playback_mode=PlaybackMode(payload.playback_mode),
        status=BattleStatus.IN_PROGRESS,
        current_round=0,
        next_turn_number=1,
        state_version=0,
    )
    session.add(battle)
    session.commit()
    session.refresh(battle)
    return battle


def create_rematch(session: Session, battle: Battle) -> Battle:
    rematch = Battle(
        fighter_a_id=battle.fighter_a_id,
        fighter_b_id=battle.fighter_b_id,
        topic=battle.topic,
        style=battle.style,
        intensity=battle.intensity,
        round_count=battle.round_count,
        playback_mode=battle.playback_mode,
        status=BattleStatus.IN_PROGRESS,
        current_round=0,
        next_turn_number=1,
        state_version=0,
        previous_battle_id=battle.id,
    )
    session.add(rematch)
    session.commit()
    session.refresh(rematch)
    return rematch


def battle_detail_dict(session: Session, battle: Battle) -> dict:
    result = None
    if battle.status in (BattleStatus.AWAITING_VOTE, BattleStatus.COMPLETED):
        result = build_result(session, battle)
    return battle_detail(session, battle, result=result)


# ---------------------------------------------------------------- turn


async def generate_turn(
    *,
    session_factory: sessionmaker[Session],
    battle_id: str,
    llm: LLMProvider | LLMProviderPair,
    expected_turn_number: int | None = None,
) -> TurnResult:
    # --- 1. cheap pre-checks (outside the lock) -----------------------------
    with session_factory() as session:
        battle = get_battle(session, battle_id)
        current_turn = battle.next_turn_number

        # Replay wins over the status check: re-sending an already-persisted turn
        # must be safe even after the battle has moved to awaiting_vote.
        if expected_turn_number is not None and expected_turn_number != current_turn:
            replay = _replay(session, battle, expected_turn_number)
            if replay is not None:
                return replay
            _assert_in_progress(battle)
            raise TurnConflictError(
                f"The battle is at turn {current_turn}, not {expected_turn_number}.",
                details={"expected": expected_turn_number, "actual": current_turn},
            )

        _assert_in_progress(battle)

    # --- 2. one generator per battle at a time ------------------------------
    async with battle_lock(battle_id) as acquired:
        if not acquired:
            raise TurnBusyError()

        # Re-read: another request may have advanced the battle while we waited.
        with session_factory() as session:
            battle = get_battle(session, battle_id)
            turn_number = battle.next_turn_number
            if expected_turn_number is not None and expected_turn_number != turn_number:
                replay = _replay(session, battle, expected_turn_number)
                if replay is not None:
                    return replay
                _assert_in_progress(battle)
                raise TurnConflictError(
                    details={"expected": expected_turn_number, "actual": turn_number}
                )
            _assert_in_progress(battle)
            round_number = turn_math.round_for_turn(turn_number)
            speaker_id = battle.fighter_a_id if turn_math.speaker_is_a(turn_number) else battle.fighter_b_id
            opponent_id = battle.fighter_b_id if turn_math.speaker_is_a(turn_number) else battle.fighter_a_id
            speaker = get_character(session, speaker_id)
            opponent = get_character(session, opponent_id)
            history = latest_verses(session, battle_id, limit=6)  # transcript shows last 3; all 6 feed the "already used" list
            memories = _memories(session, speaker.id, opponent.id)
            prompt = build_prompt(
                battle=battle,
                speaker=speaker,
                opponent=opponent,
                previous_verses=history,
                memories=memories,
                turn_number=turn_number,
                round_number=round_number,
            )
            request = VerseRequest(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
                character_name=speaker.name,
                opponent_name=opponent.name,
                turn_number=turn_number,
                metadata={"style": battle.style.value, "intensity": battle.intensity.value},
            )
            provider = (
                llm.for_fighter_a(speaker.id == battle.fighter_a_id)
                if isinstance(llm, LLMProviderPair)
                else llm
            )
            # Numbers the verse may use: only ones the topic or opponent already said.
            allowed_numbers = numbers_in(battle.topic)
            for earlier in history[-2:]:
                allowed_numbers |= numbers_in(earlier.verse_text)
            # A rebuttal must pick up a word from the opponent's latest verse.
            last_opponent = next(
                (v for v in reversed(history) if v.character_id != speaker.id), None
            )
            echo_words = (
                echo_terms(last_opponent.verse_text, battle.topic) if last_opponent else []
            )
            must_echo = frozenset(echo_words)
            # Every verse must touch the topic; short topics yield no terms and
            # the check stays off (mirrors the reply-echo mechanism).
            topic_words = topic_terms(battle.topic)
            must_touch_topic = frozenset(topic_words)

        # --- 3. provider call: NO transaction open ---------------------------
        completion = await provider.generate_verse(request)
        try:
            parsed = parse_verse(completion.text, allowed_numbers, must_echo, must_touch_topic)
        except ProviderInvalidOutputError:
            # One rewrite attempt. Still only one verse is ever saved.
            logger.info("Verse rejected for turn %d; asking for one rewrite.", turn_number)
            retry_request = replace(
                request,
                user_prompt=request.user_prompt
                + "\n\nYour last attempt was rejected. Rewrite it as 3-4 plain spoken "
                "lines, each 7-12 words, with no digits or invented numbers."
                + (
                    " Your first line must answer the opponent by using one of "
                    "their words: " + ", ".join(echo_words[:6]) + "."
                    if echo_words
                    else ""
                )
                + (
                    " The verse must mention the topic, using at least one of: "
                    + ", ".join(topic_words[:6]) + "."
                    if topic_words
                    else ""
                ),
            )
            completion = await provider.generate_verse(retry_request)
            parsed = parse_verse(completion.text, allowed_numbers, must_echo, must_touch_topic)

        # --- 4. compare-and-swap write --------------------------------------
        with session_factory() as session:
            expected_version = battle.state_version
            new_next_turn = turn_number + 1
            final_turn = turn_math.is_final_turn(turn_number, battle.round_count)
            new_status = BattleStatus.AWAITING_VOTE if final_turn else BattleStatus.IN_PROGRESS

            stmt = (
                update(Battle)
                .where(
                    Battle.id == battle_id,
                    Battle.state_version == expected_version,
                    Battle.next_turn_number == turn_number,
                    Battle.status == BattleStatus.IN_PROGRESS,
                )
                .values(
                    state_version=expected_version + 1,
                    next_turn_number=new_next_turn,
                    current_round=turn_math.round_for_turn(new_next_turn)
                    if not final_turn
                    else battle.round_count,
                    status=new_status,
                )
            )
            result = session.execute(stmt)
            if result.rowcount != 1:
                session.rollback()
                # Someone else won the race: return their verse if it exists.
                battle = get_battle(session, battle_id)
                replay = _replay(session, battle, turn_number)
                if replay is not None:
                    return replay
                raise TurnConflictError()

            verse = Verse(
                battle_id=battle_id,
                character_id=speaker.id,
                round_number=round_number,
                turn_number=turn_number,
                verse_text=parsed.verse_text,
                line_count=parsed.line_count,
                model=completion.model,
                provider=completion.provider,
            )
            session.add(verse)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                battle = get_battle(session, battle_id)
                replay = _replay(session, battle, turn_number)
                if replay is not None:
                    return replay
                raise TurnConflictError() from None

            session.refresh(verse)
            battle = get_battle(session, battle_id)
            payload = TurnResult(
                battle_payload=battle_out(battle).model_dump(mode="json"),
                verse_payload=verse_out(verse).model_dump(mode="json"),
                created=True,
            )
            logger.info(
                "battle %s turn %d generated by %s (%s)",
                battle_id,
                turn_number,
                speaker.name,
                completion.provider,
            )
            return payload


def _assert_in_progress(battle: Battle) -> None:
    if battle.status not in (BattleStatus.IN_PROGRESS, BattleStatus.CREATED):
        raise BattleNotInProgressError()


def _replay(session: Session, battle: Battle, turn_number: int) -> TurnResult | None:
    if turn_number >= battle.next_turn_number:
        return None
    verse = verse_by_turn(session, battle.id, turn_number)
    if verse is None:
        return None
    return TurnResult(
        battle_payload=battle_out(battle).model_dump(mode="json"),
        verse_payload=verse_out(verse).model_dump(mode="json"),
        created=False,
    )


def _memories(session: Session, character_id: str, opponent_id: str):
    from app.services.memory import memories_for

    return memories_for(session, character_id, opponent_id)


# ---------------------------------------------------------------- vote


def cast_vote(session: Session, battle_id: str, winner_character_id: str, voter_key: str):
    from app.core.errors import AlreadyVotedError
    from app.models import Vote

    battle = get_battle(session, battle_id)

    # Idempotent replay first: re-sending the same vote after the battle closed
    # must succeed, otherwise a retried request looks like a failure to the user.
    existing = session.scalars(
        select(Vote).where(Vote.battle_id == battle_id, Vote.voter_key == voter_key)
    ).first()
    if existing is not None:
        if existing.winner_character_id == winner_character_id:
            return existing, battle, False
        raise AlreadyVotedError("You already voted for the other robot.")

    if battle.status != BattleStatus.AWAITING_VOTE:
        if battle.status == BattleStatus.COMPLETED:
            raise BattleNotVotableError("This battle is already decided.")
        raise BattleNotVotableError()

    if winner_character_id not in (battle.fighter_a_id, battle.fighter_b_id):
        raise ValidationFailedError("That robot is not in this battle.")

    vote = Vote(
        battle_id=battle_id,
        voter_key=voter_key,
        winner_character_id=winner_character_id,
    )
    session.add(vote)

    # First vote decides the battle. Later votes still count toward the tally
    # but do not flip the winner, so a completed battle stays stable.
    from app.models.base import utcnow

    battle.status = BattleStatus.COMPLETED
    battle.winner_character_id = winner_character_id
    battle.completed_at = utcnow()
    battle.state_version += 1
    session.flush()
    record_result_memories(session, battle)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalars(
            select(Vote).where(Vote.battle_id == battle_id, Vote.voter_key == voter_key)
        ).first()
        if existing is not None and existing.winner_character_id == winner_character_id:
            battle = get_battle(session, battle_id)
            return existing, battle, False
        from app.core.errors import AlreadyVotedError

        raise AlreadyVotedError() from None

    session.refresh(vote)
    battle = get_battle(session, battle_id)
    return vote, battle, True