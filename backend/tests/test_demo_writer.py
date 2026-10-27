"""Demo Mode writer behaviour.

The scripted writer must stay honest (clearly not an LLM), and it must actually
respond to the opponent's previous verse so a demo battle reads like an exchange.
"""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from app.providers.llm.base import VerseRequest
from app.providers.llm.demo_writer import DemoWriter
from app.seeds.characters import BUILTIN_CHARACTERS
from app.services.prompt_builder import build_prompt
from app.services.verse_validator import parse_verse

TOPIC = "best antenna polish"
OPPONENT_VERSE = (
    "Your antenna looks like a bent paperclip\n"
    "Your signal drops in a light breeze"
)


def _character(index: int) -> NS:
    data = BUILTIN_CHARACTERS[index]
    return NS(
        id=data["slug"],
        name=data["name"],
        tagline=data["tagline"],
        personality=data["personality"],
        catchphrase=data["catchphrase"],
    )


def _battle() -> NS:
    return NS(style=NS(value="rap"), intensity=NS(value="spicy"), topic=TOPIC, round_count=2)


def _prompt(turn: int) -> tuple[str, str, str, str]:
    """(system, user, speaker_name, opponent_name) built by the real prompt builder.

    These fixtures deliberately come from ``build_prompt`` rather than hand-written
    strings: the previous hand-written fixtures kept the old prompt format alive
    and hid a real bug (the demo writer read a format the app no longer emits).
    """
    nova, rook = _character(0), _character(1)
    speaker, opponent = (rook, nova) if turn % 2 == 0 else (nova, rook)
    history = (
        [NS(character_id=nova.id, verse_text=OPPONENT_VERSE, turn_number=1)] if turn > 1 else []
    )
    pair = build_prompt(
        battle=_battle(),
        speaker=speaker,
        opponent=opponent,
        previous_verses=history,
        turn_number=turn,
        round_number=(turn - 1) // 2 + 1,
    )
    return pair.system_prompt, pair.user_prompt, speaker.name, opponent.name


def _request(turn: int = 2, **overrides) -> VerseRequest:
    system, user, speaker, opponent = _prompt(turn)
    kwargs = {
        "system_prompt": system,
        "user_prompt": user,
        "character_name": speaker,
        "opponent_name": opponent,
        "turn_number": turn,
        "metadata": {"style": "rap"},
    }
    kwargs.update(overrides)
    return VerseRequest(**kwargs)


@pytest.mark.asyncio
async def test_identifies_itself_as_scripted():
    completion = await DemoWriter().generate_verse(_request(2))
    assert completion.provider == "demo"
    assert completion.model == "scripted-demo-writer"
    assert completion.prompt_tokens == 0


@pytest.mark.asyncio
async def test_quotes_the_opponents_actual_line():
    completion = await DemoWriter().generate_verse(_request(2))
    assert "bent paperclip" in completion.text.lower()
    # It must never quote words from its own instructions as the opponent's.
    assert "ALREADY USED" not in completion.text
    assert "REBUTTAL" not in completion.text


@pytest.mark.asyncio
async def test_uses_the_real_topic_from_the_prompt():
    """Regression: the demo writer used to read an older prompt format and
    fall back to the literal placeholder "this showdown" for every verse."""
    for turn in (1, 2):
        completion = await DemoWriter().generate_verse(_request(turn))
        assert TOPIC in completion.text.lower()
        assert "this showdown" not in completion.text.lower()


@pytest.mark.asyncio
async def test_callbacks_do_not_nest_quotes():
    completion = await DemoWriter().generate_verse(_request(2))
    # The topic is legitimately quoted twice; what must never appear is a
    # reminder-of-a-reminder like "You said "You said ..."".
    assert '""' not in completion.text
    assert "You said You said" not in completion.text
    assert completion.text.count('"') % 2 == 0


@pytest.mark.asyncio
async def test_opening_turn_does_not_invent_an_opponent_line():
    completion = await DemoWriter().generate_verse(_request(1))
    lowered = completion.text.lower()
    assert "you said" not in lowered
    assert "cute" not in lowered


@pytest.mark.asyncio
async def test_respects_the_line_limit():
    completion = await DemoWriter().generate_verse(_request(2, max_lines=2))
    assert len(completion.text.splitlines()) == 2


@pytest.mark.asyncio
async def test_scripted_lines_satisfy_verse_word_limits():
    for style in ("rap", "roast", "debate"):
        for turn in (1, 2):
            completion = await DemoWriter().generate_verse(
                _request(turn, metadata={"style": style})
            )
            parse_verse(completion.text)
            assert not any(character.isdigit() for character in completion.text)


@pytest.mark.asyncio
async def test_the_two_robot_voices_differ():
    roster = await DemoWriter().health()
    assert roster[0] is True
    assert "not AI-generated" in roster[1]

    rook = await DemoWriter().generate_verse(_request(2))
    nova = await DemoWriter().generate_verse(_request(3))
    assert nova.text != rook.text


@pytest.mark.asyncio
async def test_is_deterministic_for_the_same_input():
    writer = DemoWriter()
    first = await writer.generate_verse(_request(2))
    second = await writer.generate_verse(_request(2))
    assert first.text == second.text
