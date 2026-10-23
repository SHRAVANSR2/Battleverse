"""One real Groq call, using the production adapter and prompt builder.

    python -m app.scripts.groq_smoke

Requires GROQ_API_KEY in the environment or repo-root .env. Exits non-zero if
the key is missing or the call fails. Prints the model and the generated verse
so you can see real output, not a summary.
"""

from __future__ import annotations

import asyncio
import sys

from app.core.config import get_settings
from app.providers.llm.registry import build_llm_provider
from app.providers.llm.base import VerseRequest
from app.services.verse_validator import parse_verse

SYSTEM = """You are Rook Blaze, a cartoon battle-robot. Warm heart, colder delivery.
Personality: deadpan, dry, laconic. Traits: unimpressed, precise, secretly sentimental.
You are battling Nova Vex in a rap battle with punchlines and rhyme.

Reply with ONLY a JSON object with keys: "verse_text" (4 short lines separated by
newline characters), "line_count" (integer), "callback_reference" (short phrase).

Every verse must be newly written. Reference the opponent's most recent line.
No slurs, no cruelty about real people."""

USER = """Topic: who has the best antenna

Round 1 of 3. This is your turn (turn 2).

Recent battle transcript (oldest first):
Nova Vex (YOU): Oh honey, hold my spark — my antenna is the crown of the room,
I glimmer, I shimmer, I literally bloom.

Write your next rap battle verse aimed at Nova Vex. 4 lines maximum."""


async def main() -> int:
    settings = get_settings()
    if settings.demo_mode:
        print(
            "No GROQ_API_KEY configured — refusing to run. "
            "Add it to .env and retry.",
            file=sys.stderr,
        )
        return 2

    print(f"model: {settings.llm_model}")
    provider = build_llm_provider(settings)
    request = VerseRequest(
        system_prompt=SYSTEM,
        user_prompt=USER,
        character_name="Rook Blaze",
        opponent_name="Nova Vex",
        turn_number=2,
        metadata={"style": "rap", "intensity": "playful"},
    )
    completion = await provider.generate_verse(request)
    parsed = parse_verse(completion.text)

    print(f"provider: {completion.provider}  model_returned: {completion.model}")
    print(f"tokens:   prompt={completion.prompt_tokens} completion={completion.completion_tokens}")
    print(f"lines:    {parsed.line_count}")
    print("-" * 50)
    print(parsed.verse_text)
    print("-" * 50)
    if parsed.callback_reference:
        print(f"callback: {parsed.callback_reference}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))