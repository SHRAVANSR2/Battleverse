"""Invented numbers are rejected; the engine asks for one rewrite, then gives up."""

from __future__ import annotations

import asyncio

import pytest

from app.core.errors import ProviderInvalidOutputError
from app.providers.llm.base import LLMProvider, RawCompletion
from app.services import battle_engine
from app.services.verse_validator import numbers_in, parse_verse

GOOD = (
    "Your garden grows slower than my patience today\n"
    "You water the weeds and then call it art\n"
    "I plant every punchline and watch them all bloom\n"
    "Your roses wilt fast when I walk through the door"
)
WITH_NUMBER = GOOD.replace("slower than my patience today", "3.14159 times slower than my patience")


def test_numbers_in_finds_digit_numbers():
    assert numbers_in("error 404 and 3.14 and 1,237") == {"404", "3.14", "1,237"}
    assert numbers_in("no digits here") == frozenset()


def test_number_words_are_found_but_small_ones_are_fine():
    assert numbers_in("a million bugs, fifty percent faster") == {"million", "fifty", "percent"}
    assert numbers_in("two left feet and no one cares") == frozenset()


def test_spelled_out_stats_are_rejected():
    spelled = GOOD.replace("slower than my patience today", "a million times slower than my patience")
    with pytest.raises(ProviderInvalidOutputError):
        parse_verse(spelled)


def test_invented_numbers_are_rejected():
    with pytest.raises(ProviderInvalidOutputError):
        parse_verse(WITH_NUMBER)


def test_numbers_from_topic_or_opponent_are_allowed():
    parsed = parse_verse(WITH_NUMBER, allowed_numbers=frozenset({"3.14159"}))
    assert "3.14159" in parsed.verse_text


def test_clean_verse_still_parses():
    assert parse_verse(GOOD).line_count == 4


class ScriptedProvider(LLMProvider):
    provider_name = "groq"
    model_name = "scripted"

    def __init__(self, outputs: list[str]):
        self.outputs = outputs
        self.requests = []

    async def generate_verse(self, request):
        self.requests.append(request)
        text = self.outputs[min(len(self.requests) - 1, len(self.outputs) - 1)]
        return RawCompletion(text=text, model=self.model_name, provider=self.provider_name)

    async def health(self):
        return True, "ok"


def _battle(session, characters):
    from app.schemas.battle import CreateBattleIn

    return battle_engine.create_battle(
        session,
        CreateBattleIn(
            fighter_a_id=characters[0]["id"],
            fighter_b_id=characters[1]["id"],
            topic="best garden tools",
            round_count=1,
        ),
    )


def test_engine_asks_for_one_rewrite_and_saves_one_verse(client, characters, session, session_factory):
    battle = _battle(session, characters)
    provider = ScriptedProvider([WITH_NUMBER, GOOD])

    result = asyncio.run(
        battle_engine.generate_turn(session_factory=session_factory, battle_id=battle.id, llm=provider)
    )

    assert result.created is True
    assert len(provider.requests) == 2
    assert "rejected" in provider.requests[1].user_prompt
    assert "3.14159" not in result.verse_payload["verse_text"]


def test_engine_gives_up_after_one_rewrite_and_changes_nothing(client, characters, session, session_factory):
    battle = _battle(session, characters)
    provider = ScriptedProvider([WITH_NUMBER])

    with pytest.raises(ProviderInvalidOutputError):
        asyncio.run(
            battle_engine.generate_turn(session_factory=session_factory, battle_id=battle.id, llm=provider)
        )

    assert len(provider.requests) == 2
    session.expire_all()
    assert battle_engine.get_battle(session, battle.id).next_turn_number == 1


# ---- rebuttals must answer the opponent -------------------------------------

from app.services.prompt_builder import echo_terms  # noqa: E402

ANSWERS_HAMSTER = (
    "Your hamster wheel stops when the power dies\n"
    "I debug in daylight while you chase glowing sticks\n"
    "You code like a nap that never ends\n"
    "Keep spinning while I ship the finished work"
)
IGNORES_OPPONENT = (
    "Your syntax looks like toddler magnets on the fridge\n"
    "Hearing you type is like a broken alarm clock\n"
    "Maybe take a nap instead of fixing bugs\n"
    "Keep talking until the crowd goes home early"
)


def test_echo_terms_skips_stopwords_topic_and_numbers():
    terms = echo_terms("Your hamster wheel spins 404 times about coding", "coding")
    assert "hamster" in terms and "wheel" in terms
    assert "coding" not in terms and "404" not in terms and "about" not in terms


def test_rebuttal_that_ignores_the_opponent_is_rejected():
    with pytest.raises(ProviderInvalidOutputError):
        parse_verse(IGNORES_OPPONENT, must_echo=frozenset({"hamster", "wheel"}))


def test_rebuttal_that_answers_the_opponent_is_accepted():
    assert parse_verse(ANSWERS_HAMSTER, must_echo=frozenset({"hamster", "wheel"})).line_count == 4


def test_plural_form_still_counts_as_an_echo():
    plural = ANSWERS_HAMSTER.replace("hamster wheel", "hamsters wheels")
    assert parse_verse(plural, must_echo=frozenset({"hamster"})).line_count == 4


def test_opening_verse_has_nothing_to_echo():
    assert parse_verse(IGNORES_OPPONENT).line_count == 4


# ---- every verse must touch the topic ---------------------------------------

from app.services.prompt_builder import topic_terms  # noqa: E402


def test_topic_terms_skips_stopwords_and_numbers():
    terms = topic_terms("who has the best antenna")
    assert terms == ["antenna"]
    assert topic_terms("best 404s") == []


def test_verse_that_ignores_the_topic_is_rejected():
    off_topic = (
        "Your syntax looks like toddler magnets on the fridge\n"
        "Hearing you type is like a broken alarm clock\n"
        "Maybe take a nap instead of fixing bugs\n"
        "Keep talking until the crowd goes home early"
    )
    with pytest.raises(ProviderInvalidOutputError):
        parse_verse(off_topic, must_touch_topic=frozenset({"antenna"}))


def test_verse_that_mentions_the_topic_is_accepted():
    on_topic = (
        "Your antenna bends under my signal weight\n"
        "Hearing you type is like a broken alarm clock\n"
        "Maybe take a nap instead of fixing bugs\n"
        "Keep talking until the crowd goes home early"
    )
    assert parse_verse(on_topic, must_touch_topic=frozenset({"antenna"})).line_count == 4


def test_plural_topic_word_still_counts():
    on_topic = (
        "Your antennas bend under my signal weight\n"
        "Hearing you type is like a broken alarm clock\n"
        "Maybe take a nap instead of fixing bugs\n"
        "Keep talking until the crowd goes home early"
    )
    assert parse_verse(on_topic, must_touch_topic=frozenset({"antenna"})).line_count == 4


def test_short_topic_disables_the_check():
    assert parse_verse(IGNORES_OPPONENT, must_touch_topic=frozenset()).line_count == 4


def test_engine_rewrites_a_verse_that_ignores_the_topic(
    client, characters, session, session_factory
):
    battle = _battle(session, characters)
    provider = ScriptedProvider([IGNORES_OPPONENT, GOOD])

    result = asyncio.run(
        battle_engine.generate_turn(session_factory=session_factory, battle_id=battle.id, llm=provider)
    )

    assert result.created is True
    assert len(provider.requests) == 2
    assert "mention the topic" in provider.requests[1].user_prompt
    assert "garden" in provider.requests[1].user_prompt


ANSWERS_GARDEN = (
    "Your garden grows slower than my patience, friend\n"
    "I trim your weeds while you admire them\n"
    "Water all you want, nothing here blooms\n"
    "Next time bring a shovel and some courage"
)


def test_engine_rewrites_a_rebuttal_that_ignores_the_opponent(
    client, characters, session, session_factory
):
    battle = _battle(session, characters)
    first = ScriptedProvider([GOOD])
    asyncio.run(
        battle_engine.generate_turn(session_factory=session_factory, battle_id=battle.id, llm=first)
    )

    second = ScriptedProvider([IGNORES_OPPONENT, ANSWERS_GARDEN])
    result = asyncio.run(
        battle_engine.generate_turn(session_factory=session_factory, battle_id=battle.id, llm=second)
    )

    assert result.created is True
    assert len(second.requests) == 2
    assert "answer the opponent" in second.requests[1].user_prompt
    assert "garden" in result.verse_payload["verse_text"].lower()