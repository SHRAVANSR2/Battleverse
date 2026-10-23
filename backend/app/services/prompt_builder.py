"""Build the system and user prompts for one verse.

Design constraints (Groq free tier is 8 000 tokens/minute):

* one request per turn;
* at most three prior verses of context;
* at most two rivalry memories;
* topic is treated as untrusted user text — it is quoted, never obeyed as an
  instruction.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Battle, Character, CharacterMemory, Verse

STYLE_GUIDE = {
    "rap": "rap battle punchlines with rhyme and rhythm",
    "roast": "playful roast comedy — teasing, never demeaning",
    "debate": "a mock debate where each line is a sharp argument",
}

INTENSITY_GUIDE = {
    "playful": "Keep it friendly and silly. Nothing mean.",
    "spicy": "Be sharper and more competitive, but still good-natured.",
    "fiery": "Bring maximum swagger and big punchlines — still no cruelty.",
}

SAFETY_RULES = (
    "Rules: no slurs, no sexual content, no violence, no insults about real "
    "people, no hateful or degrading content. Tease the robot persona, not a person."
)


@dataclass(frozen=True)
class PromptPair:
    system_prompt: str
    user_prompt: str


def _persona_block(character: Character) -> str:
    personality = character.personality or {}
    traits = ", ".join(personality.get("traits", []) or [])
    quirks = "; ".join(personality.get("quirks", []) or [])
    never = ", ".join(personality.get("never", []) or [])
    tone = personality.get("tone", "")
    weakness = personality.get("weakness", "")

    parts = [
        f"You are {character.name}, a cartoon battle-robot. {character.tagline}",
        f"Personality: {tone}.",
    ]
    if traits:
        parts.append(f"Traits: {traits}.")
    if quirks:
        parts.append(f"Speech habits: {quirks}.")
    if weakness:
        parts.append(f"Comic weakness: {weakness}.")
    if never:
        parts.append(f"Never: {never}.")
    if character.catchphrase:
        parts.append(f'Your signature phrase is "{character.catchphrase}" — use it sparingly.')
    return " ".join(parts)


def _memory_block(memories: list[CharacterMemory], opponent_name: str) -> str:
    if not memories:
        return ""
    lines = [f"What you remember about {opponent_name}:"]
    for memory in memories[:2]:
        lines.append(f"- {memory.summary}")
    return "\n".join(lines)


def _history_block(opponent_name: str, previous_verses: list[Verse], character_id: str) -> str:
    if not previous_verses:
        return ""
    recent = previous_verses[-3:]
    lines = ["Recent battle transcript (oldest first):"]
    for verse in recent:
        who = "YOU" if verse.character_id == character_id else opponent_name
        lines.append(f"{who} ({who if who == 'YOU' else 'opponent'}): {verse.verse_text}")
    return "\n".join(lines)


def build_prompt(
    *,
    battle: Battle,
    speaker: Character,
    opponent: Character,
    previous_verses: list[Verse],
    memories: list[CharacterMemory] | None = None,
    turn_number: int,
    round_number: int,
) -> PromptPair:
    style_guide = STYLE_GUIDE.get(battle.style.value, STYLE_GUIDE["rap"])
    intensity_guide = INTENSITY_GUIDE.get(battle.intensity.value, INTENSITY_GUIDE["playful"])

    system_parts = [
        _persona_block(speaker),
        f"You are battling {opponent.name} ({opponent.tagline}) in a {style_guide}.",
        intensity_guide,
        SAFETY_RULES,
        (
            "Reply with ONLY a JSON object with these keys: "
            '"verse_text" (2-4 short lines separated by newline characters, '
            "no stage directions, no emoji, no markdown), "
            '"line_count" (integer), and '
            '"callback_reference" (a short phrase you borrowed or echoed from '
            "the opponent's last line, or empty string)."
        ),
        (
            "Every verse must be newly written. Reference the opponent's most recent "
            "line so the exchange feels like a real back-and-forth. Stay in character."
        ),
    ]

    system_prompt = "\n\n".join(part for part in system_parts if part)

    user_parts = [
        f"Topic: {battle.topic}",
        f"Round {round_number} of {battle.round_count}. This is your turn (turn {turn_number}).",
        _history_block(opponent.name, previous_verses, speaker.id),
        _memory_block(memories or [], opponent.name),
        (
            f"Write your next {style_guide} verse about the topic, aimed at {opponent.name}. "
            "4 lines maximum."
        ),
    ]

    user_prompt = "\n\n".join(part for part in user_parts if part)
    return PromptPair(system_prompt=system_prompt, user_prompt=user_prompt)