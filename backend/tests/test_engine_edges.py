"""Correctness edges: idempotency, CAS races, prompt contents, voting, memory."""

from __future__ import annotations

import asyncio

import pytest

from app.core.errors import (
    AlreadyVotedError,
    BattleNotInProgressError,
    BattleNotVotableError,
    ProviderUnavailableError,
    TurnConflictError,
    ValidationFailedError,
)
from app.models import Battle, BattleStatus, Verse
from app.providers.llm.base import LLMProvider, RawCompletion
from app.providers.llm.registry import LLMProviderPair
from app.services import battle_engine
from app.services.battle_queries import get_battle
from app.services.prompt_builder import build_prompt
from app.services.results import build_result


# Spelled out on purpose: the validator rejects invented digits.
_TURN_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


class CountingProvider(LLMProvider):
    provider_name = "demo"
    model_name = "counting"

    def __init__(self, fail_after: int | None = None, provider_name: str = "demo"):
        self.calls = 0
        self.fail_after = fail_after
        self.requests = []
        self.provider_name = provider_name
        self.model_name = f"{provider_name}-test-model"

    async def generate_verse(self, request):
        self.calls += 1
        self.requests.append(request)
        if self.fail_after is not None and self.calls > self.fail_after:
            raise ProviderUnavailableError()
        return RawCompletion(
            text=(
                f"First clean antenna line from {request.character_name} lands clearly\n"
                f"Another clear antenna response for turn {_TURN_WORDS[request.turn_number % 10]} lands cleanly now"
            ),
            model=self.model_name,
            provider=self.provider_name,
        )

    async def health(self):
        return True, "ok"


def _battle(session, characters, rounds=2):
    from app.schemas.battle import CreateBattleIn

    return battle_engine.create_battle(
        session,
        CreateBattleIn(
            fighter_a_id=characters[0]["id"],
            fighter_b_id=characters[1]["id"],
            topic="best antenna polish",
            round_count=rounds,
        ),
    )


def test_idempotent_replay_does_not_call_provider(client, characters, session, session_factory):
    battle = _battle(session, characters)
    provider = CountingProvider()

    first = asyncio.run(
        battle_engine.generate_turn(
            session_factory=session_factory, battle_id=battle.id, llm=provider
        )
    )
    assert first.created is True

    replay = asyncio.run(
        battle_engine.generate_turn(
            session_factory=session_factory,
            battle_id=battle.id,
            llm=provider,
            expected_turn_number=1,
        )
    )
    assert replay.created is False
    assert provider.calls == 1
    assert replay.verse_payload["id"] == first.verse_payload["id"]


def test_fighter_side_selects_its_assigned_provider(
    client, characters, session, session_factory
):
    battle = _battle(session, characters)
    groq = CountingProvider(provider_name="groq")
    gemini = CountingProvider(provider_name="gemini")
    providers = LLMProviderPair(fighter_a=groq, fighter_b=gemini)

    first = asyncio.run(
        battle_engine.generate_turn(
            session_factory=session_factory, battle_id=battle.id, llm=providers
        )
    )
    second = asyncio.run(
        battle_engine.generate_turn(
            session_factory=session_factory,
            battle_id=battle.id,
            llm=providers,
            expected_turn_number=2,
        )
    )

    assert first.verse_payload["provider"] == "groq"
    assert second.verse_payload["provider"] == "gemini"
    assert groq.calls == gemini.calls == 1


class FlakyGeminiProvider(LLMProvider):
    """Gemini side that 503s on the first call, then answers like the real
    fallback retry would (the adapter picks the model; the engine just sees
    a provider that raised once and then succeeds)."""

    provider_name = "gemini"
    model_name = "gemini-test-model"

    def __init__(self):
        self.calls = 0

    async def generate_verse(self, request):
        self.calls += 1
        if self.calls == 1:
            raise ProviderUnavailableError()
        return RawCompletion(
            text=(
                "You called that line clear, but clearly not\n"
                "Your antenna polish peels like old paint"
            ),
            model=self.model_name,
            provider=self.provider_name,
        )

    async def health(self):
        return True, "ok"


def test_gemini_side_503_then_retry_saves_gemini_tagged_verse(
    client, characters, session, session_factory
):
    """A Gemini 503 must not advance the turn; the client retry (same turn
    number) saves exactly one verse, honestly tagged 'gemini'."""
    battle = _battle(session, characters, rounds=1)
    providers = LLMProviderPair(
        fighter_a=CountingProvider(provider_name="groq"),
        fighter_b=FlakyGeminiProvider(),
    )

    asyncio.run(
        battle_engine.generate_turn(
            session_factory=session_factory, battle_id=battle.id, llm=providers
        )
    )

    with pytest.raises(ProviderUnavailableError):
        asyncio.run(
            battle_engine.generate_turn(
                session_factory=session_factory,
                battle_id=battle.id,
                llm=providers,
                expected_turn_number=2,
            )
        )
    with session_factory() as check:
        assert check.query(Verse).filter_by(battle_id=battle.id).count() == 1
        assert get_battle(check, battle.id).next_turn_number == 2

    result = asyncio.run(
        battle_engine.generate_turn(
            session_factory=session_factory,
            battle_id=battle.id,
            llm=providers,
            expected_turn_number=2,
        )
    )
    assert result.created is True
    assert result.verse_payload["provider"] == "gemini"
    with session_factory() as check:
        assert check.query(Verse).filter_by(battle_id=battle.id).count() == 2


def test_failure_leaves_battle_untouched(client, characters, session, session_factory):
    battle = _battle(session, characters)
    provider = CountingProvider(fail_after=0)

    with pytest.raises(ProviderUnavailableError):
        asyncio.run(
            battle_engine.generate_turn(
                session_factory=session_factory, battle_id=battle.id, llm=provider
            )
        )

    with session_factory() as check:
        reloaded = get_battle(check, battle.id)
        assert reloaded.next_turn_number == 1
        assert reloaded.status == BattleStatus.IN_PROGRESS
        assert check.query(Verse).filter_by(battle_id=battle.id).count() == 0


def test_conflicting_turn_number_rejected(client, characters, session, session_factory):
    battle = _battle(session, characters)
    provider = CountingProvider()
    asyncio.run(
        battle_engine.generate_turn(
            session_factory=session_factory, battle_id=battle.id, llm=provider
        )
    )
    with pytest.raises(TurnConflictError) as caught:
        asyncio.run(
            battle_engine.generate_turn(
                session_factory=session_factory,
                battle_id=battle.id,
                llm=provider,
                expected_turn_number=5,
            )
        )
    assert caught.value.details == {"expected": 5, "actual": 2}


def test_concurrent_duplicate_turns_produce_one_verse(client, characters, session, session_factory):
    """Two requests both expecting turn 1 (a double-click) -> one verse, one call."""
    battle = _battle(session, characters)
    provider = CountingProvider()

    async def race():
        return await asyncio.gather(
            battle_engine.generate_turn(
                session_factory=session_factory,
                battle_id=battle.id,
                llm=provider,
                expected_turn_number=1,
            ),
            battle_engine.generate_turn(
                session_factory=session_factory,
                battle_id=battle.id,
                llm=provider,
                expected_turn_number=1,
            ),
            return_exceptions=True,
        )

    results = asyncio.run(race())
    with session_factory() as check:
        verses = list(check.query(Verse).filter_by(battle_id=battle.id))
        battlefield = get_battle(check, battle.id)

    assert len(verses) == 1, f"expected exactly one verse, got {len(verses)}"
    assert battlefield.next_turn_number == 2
    assert provider.calls == 1, "the provider must be called exactly once"
    successes = [r for r in results if not isinstance(r, Exception)]
    assert len(successes) == 2, "both requests should get a usable answer"
    assert {r.created for r in successes} == {True, False}


def test_sequential_calls_without_expected_advance(client, characters, session, session_factory):
    """No expected_turn_number means 'advance', so two calls make two turns."""
    battle = _battle(session, characters)
    provider = CountingProvider()
    for _ in range(2):
        asyncio.run(
            battle_engine.generate_turn(
                session_factory=session_factory, battle_id=battle.id, llm=provider
            )
        )
    with session_factory() as check:
        turns = sorted(
            v.turn_number for v in check.query(Verse).filter_by(battle_id=battle.id)
        )
    assert turns == [1, 2]
    assert provider.calls == 2


def test_prompt_contains_opponent_line_and_persona(session, characters):
    from app.models import Character
    from app.schemas.battle import CreateBattleIn

    battle = _battle(session, characters)
    speaker = session.get(Character, characters[0]["id"])
    opponent = session.get(Character, characters[1]["id"])
    prior = Verse(
        battle_id=battle.id,
        character_id=opponent.id,
        round_number=1,
        turn_number=1,
        verse_text="My antenna is the shiniest in town",
        line_count=1,
        model="x",
        provider="demo",
    )
    session.add(prior)
    session.commit()

    prompt = build_prompt(
        battle=battle,
        speaker=speaker,
        opponent=opponent,
        previous_verses=[prior],
        memories=[],
        turn_number=2,
        round_number=1,
    )
    assert opponent.name in prompt.system_prompt
    assert "shiniest in town" in prompt.user_prompt
    assert "best antenna polish" in prompt.user_prompt
    assert "JSON" in prompt.system_prompt
    # Persona specifics from the seed
    assert "chirpy" in prompt.system_prompt or "show-off" in prompt.system_prompt


def test_prompt_history_is_bounded(session, characters):
    from app.models import Character

    battle = _battle(session, characters, rounds=5)
    speaker = session.get(Character, characters[0]["id"])
    opponent = session.get(Character, characters[1]["id"])
    for turn in range(1, 8):
        session.add(
            Verse(
                battle_id=battle.id,
                character_id=characters[turn % 2]["id"],
                round_number=(turn - 1) // 2 + 1,
                turn_number=turn,
                verse_text=f"line marker {turn}",
                line_count=1,
                model="x",
                provider="demo",
            )
        )
    session.commit()
    verses = list(session.query(Verse).filter_by(battle_id=battle.id).order_by(Verse.turn_number))
    prompt = build_prompt(
        battle=battle,
        speaker=speaker,
        opponent=opponent,
        previous_verses=verses,
        memories=[],
        turn_number=8,
        round_number=4,
    )
    assert "line marker 5" in prompt.user_prompt
    assert "line marker 7" in prompt.user_prompt
    assert "line marker 1" not in prompt.user_prompt


def test_vote_rules(client, characters, session, session_factory):
    battle = _battle(session, characters, rounds=1)
    provider = CountingProvider()
    for _ in range(2):
        asyncio.run(
            battle_engine.generate_turn(
                session_factory=session_factory, battle_id=battle.id, llm=provider
            )
        )

    with session_factory() as db:
        # Voter cannot pick a robot that is not fighting.
        with pytest.raises(ValidationFailedError):
            battle_engine.cast_vote(db, battle.id, "not-a-fighter", "voter-1234")

        vote, _, created = battle_engine.cast_vote(
            db, battle.id, characters[0]["id"], "voter-1234"
        )
        assert created is True

        again, _, created_again = battle_engine.cast_vote(
            db, battle.id, characters[0]["id"], "voter-1234"
        )
        assert created_again is False
        assert again.id == vote.id

        with pytest.raises(AlreadyVotedError):
            battle_engine.cast_vote(db, battle.id, characters[1]["id"], "voter-1234")

        with pytest.raises(BattleNotVotableError):
            battle_engine.cast_vote(db, battle.id, characters[0]["id"], "voter-9999")

        result = build_result(db, get_battle(db, battle.id))
        assert result.winner is not None
        assert result.winner.character_id == characters[0]["id"]


def test_vote_before_finish_rejected(client, characters, session, session_factory):
    battle = _battle(session, characters, rounds=2)
    with session_factory() as db:
        with pytest.raises(BattleNotVotableError):
            battle_engine.cast_vote(db, battle.id, characters[0]["id"], "voter-1234")


def test_memory_is_written_and_injected(client, characters, session, session_factory):
    from app.services.memory import memories_for

    battle = _battle(session, characters, rounds=1)
    provider = CountingProvider()
    for _ in range(2):
        asyncio.run(
            battle_engine.generate_turn(
                session_factory=session_factory, battle_id=battle.id, llm=provider
            )
        )
    with session_factory() as db:
        battle_engine.cast_vote(db, battle.id, characters[0]["id"], "voter-1234")

    with session_factory() as db:
        winner_memories = memories_for(db, characters[0]["id"], characters[1]["id"])
        loser_memories = memories_for(db, characters[1]["id"], characters[0]["id"])
    assert len(winner_memories) == 1
    assert "Beat" in winner_memories[0].summary
    assert len(loser_memories) == 1
    # The loser's memory must name the winner (not the "the winner" fallback)…
    assert f"Lost to {characters[0]['name']}" in loser_memories[0].summary
    # …and neither memory may carry the old topic, which leaks into future prompts.
    for memory in [*winner_memories, *loser_memories]:
        assert "antenna" not in memory.summary

    # And the rematch prompt must contain it.
    with session_factory() as db:
        original = get_battle(db, battle.id)
        rematch = battle_engine.create_rematch(db, original)
        rematch_memories = memories_for(db, characters[0]["id"], characters[1]["id"])
        assert rematch.previous_battle_id == original.id
        assert rematch_memories, "rivalry memory must survive into the rematch"

        from app.models import Character

        prompt = build_prompt(
            battle=rematch,
            speaker=db.get(Character, characters[0]["id"]),
            opponent=db.get(Character, characters[1]["id"]),
            previous_verses=[],
            memories=rematch_memories,
            turn_number=1,
            round_number=1,
        )
    assert winner_memories[0].summary[:40] in prompt.user_prompt


def test_turns_rejected_when_not_in_progress(client, characters, session, session_factory):
    battle = _battle(session, characters, rounds=1)
    provider = CountingProvider()
    for _ in range(2):
        asyncio.run(
            battle_engine.generate_turn(
                session_factory=session_factory, battle_id=battle.id, llm=provider
            )
        )
    with pytest.raises(BattleNotInProgressError):
        asyncio.run(
            battle_engine.generate_turn(
                session_factory=session_factory, battle_id=battle.id, llm=provider
            )
        )


def test_battle_status_flips_to_awaiting_vote(session_factory, session, characters):
    battle = _battle(session, characters, rounds=1)
    provider = CountingProvider()
    result = None
    for _ in range(2):
        result = asyncio.run(
            battle_engine.generate_turn(
                session_factory=session_factory, battle_id=battle.id, llm=provider
            )
        )
    assert result is not None
    assert result.battle_payload["status"] == "awaiting_vote"
    with session_factory() as db:
        stored = db.get(Battle, battle.id)
        assert stored.status == BattleStatus.AWAITING_VOTE