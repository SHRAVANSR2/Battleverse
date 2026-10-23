"""Demo Mode writer behaviour.

The scripted writer must stay honest (clearly not an LLM), and it must actually
respond to the opponent's previous verse so a demo battle reads like an exchange.
"""

from __future__ import annotations

import pytest

from app.providers.llm.base import VerseRequest
from app.providers.llm.demo_writer import DemoWriter

OPPONENT_VERSE = (
    "Buckle up, bolts-for-brains: the topic is \"best antenna polish\", and I came to rhyme,\n"
    "My punchline on \"best antenna polish\" is mean, serene, and clean,\n"
    "Your punchline is clean. Mine is mean, every time,\n"
    "Round 1 goes to me. Keep up, Rook Blaze."
)

USER_PROMPT = "\n\n".join(
    [
        'Topic: best antenna polish',
        "Round 1 of 3. This is your turn (turn 2).",
        "Recent battle transcript (oldest first):\n"
        f"Nova Vex (opponent): {OPPONENT_VERSE}",
        "Write your next rap battle punchlines verse about the topic, aimed at Nova Vex. "
        "4 lines maximum.",
    ]
)

OPENING_PROMPT = "\n\n".join(
    [
        "Topic: best antenna polish",
        "Round 1 of 3. This is your turn (turn 1).",
        "Write your next rap battle punchlines verse about the topic, aimed at Rook Blaze. "
        "4 lines maximum.",
    ]
)


def _request(user_prompt: str, turn: int = 2) -> VerseRequest:
    return VerseRequest(
        system_prompt="ignored by the demo writer",
        user_prompt=user_prompt,
        character_name="Rook Blaze" if turn % 2 == 0 else "Nova Vex",
        opponent_name="Nova Vex" if turn % 2 == 0 else "Rook Blaze",
        turn_number=turn,
        metadata={"style": "rap"},
    )


@pytest.mark.asyncio
async def test_identifies_itself_as_scripted():
    completion = await DemoWriter().generate_verse(_request(USER_PROMPT))
    assert completion.provider == "demo"
    assert completion.model == "scripted-demo-writer"
    assert completion.prompt_tokens == 0


@pytest.mark.asyncio
async def test_quotes_the_opponents_actual_line():
    completion = await DemoWriter().generate_verse(_request(USER_PROMPT))
    assert "punchline" in completion.text.lower()
    # It must never quote words from its own instructions as the opponent's.
    assert "4 lines maximum" not in completion.text
    assert "Write your next" not in completion.text


@pytest.mark.asyncio
async def test_callbacks_do_not_nest_quotes():
    completion = await DemoWriter().generate_verse(_request(USER_PROMPT))
    # The topic is legitimately quoted twice; what must never appear is a
    # reminder-of-a-reminder like "You said "You said ..."".
    assert '""' not in completion.text
    assert "You said You said" not in completion.text
    assert completion.text.count('"') % 2 == 0


@pytest.mark.asyncio
async def test_opening_turn_does_not_invent_an_opponent_line():
    completion = await DemoWriter().generate_verse(_request(OPENING_PROMPT, turn=1))
    lowered = completion.text.lower()
    assert "you said" not in lowered
    assert "cute" not in lowered
    assert "best antenna polish" in lowered


@pytest.mark.asyncio
async def test_respects_the_line_limit():
    request = VerseRequest(
        system_prompt="",
        user_prompt=USER_PROMPT,
        character_name="Rook Blaze",
        opponent_name="Nova Vex",
        turn_number=2,
        max_lines=2,
        metadata={"style": "rap"},
    )
    completion = await DemoWriter().generate_verse(request)
    assert len(completion.text.splitlines()) == 2


@pytest.mark.asyncio
async def test_the_two_robot_voices_differ():
    roster = await DemoWriter().health()
    assert roster[0] is True
    assert "not AI-generated" in roster[1]

    rook = await DemoWriter().generate_verse(_request(USER_PROMPT, turn=2))
    nova = await DemoWriter().generate_verse(_request(USER_PROMPT, turn=3))
    assert nova.text != rook.text


@pytest.mark.asyncio
async def test_is_deterministic_for_the_same_input():
    writer = DemoWriter()
    first = await writer.generate_verse(_request(USER_PROMPT))
    second = await writer.generate_verse(_request(USER_PROMPT))
    assert first.text == second.text
