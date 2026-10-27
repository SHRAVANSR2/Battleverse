"""Roster, rap-shaping and filler-stripping behaviour."""

from types import SimpleNamespace as NS

from app.providers.tts.voices import VOICE_IDS
from app.seeds.characters import BUILTIN_CHARACTERS
from app.services.prompt_builder import build_prompt
from app.services.speech_text import shape_for_speech
from app.services.verse_validator import parse_verse


def test_four_distinct_robots_with_known_voices():
    assert len(BUILTIN_CHARACTERS) == 4
    assert len({c["slug"] for c in BUILTIN_CHARACTERS}) == 4
    assert len({c["voice_id"] for c in BUILTIN_CHARACTERS}) == 4, "every robot sounds different"
    assert len({c["accent"] for c in BUILTIN_CHARACTERS}) == 4
    for character in BUILTIN_CHARACTERS:
        assert character["voice_id"] in VOICE_IDS
        assert character["personality"]["roast_style"]
        assert character["personality"]["flow"]


def test_interjection_openers_are_stripped_but_real_words_survive():
    parsed = parse_verse(
        '{"verse_text": "Whoa! Your code compiles on luck every single morning\\n'
        "Meh. You call that loop clean code? It crashes by lunch\\n"
        "Understatement: your tab is a bedtime story nobody wants to finish\\n"
        'Well-oiled bots beat you, pal, before the coffee gets cold."}'
    )
    lines = parsed.verse_text.splitlines()
    assert lines[0] == "Your code compiles on luck every single morning"
    assert lines[1] == "You call that loop clean code? It crashes by lunch"
    assert lines[2] == "Your tab is a bedtime story nobody wants to finish"
    assert lines[3].startswith("Well-oiled")


def test_rap_gets_a_pause_after_every_bar_and_roast_is_untouched():
    text = "First bar here\nSecond bar here\nThird bar here\nFourth bar here"
    assert shape_for_speech(text, "rap") == (
        "First bar here, Second bar here. Third bar here, Fourth bar here."
    )
    assert shape_for_speech(text, "roast") == text


def _battle(style):
    return NS(
        style=NS(value=style), intensity=NS(value="spicy"), topic="Debugging", round_count=2
    )


def _char(slug_index):
    data = BUILTIN_CHARACTERS[slug_index]
    return NS(
        id=data["slug"],
        name=data["name"],
        tagline=data["tagline"],
        personality=data["personality"],
        catchphrase=data["catchphrase"],
    )


def test_prompt_prioritizes_natural_short_jokes_without_forcing_numbers():
    for style in ("rap", "roast", "debate"):
        prompt = build_prompt(
            battle=_battle(style),
            speaker=_char(2),
            opponent=_char(3),
            previous_verses=[],
            turn_number=1,
            round_number=1,
        )
        system = prompt.system_prompt
        assert "7-12 words" in system
        assert "one clear joke" in system
        assert "natural spoken English" in system
        assert "Do not force a rhyme, metaphor, callback, catchphrase" in system
        assert "Do not use numbers or quantities, in digits or words" in system
        assert "never invent or alter them" in system
        assert "Light it up, buttercup" not in system
        assert "syllables" not in system and "MULTISYLLABIC" not in system
        assert '"topic_terms"' not in system
        assert "Example of natural timing" not in system
        assert "backhanded compliment" in system  # Baron's own roast style
        assert "Gizmo Jinx" in system  # opponent named


def test_fresh_material_rule_does_not_request_replacement_numbers():
    earlier = [
        NS(
            character_id="gizmo-jinx",
            verse_text="Your hamster wheel crashed 1,732 lines\nNeon disco debugger shines",
        ),
        NS(character_id="nova-vex", verse_text="Coffee grinder beats your nap code"),
        NS(character_id="gizmo-jinx", verse_text="Your sunlit scripts need a manual"),
    ]
    prompt = build_prompt(
        battle=_battle("roast"),
        speaker=_char(0),
        opponent=_char(3),
        previous_verses=earlier,
        turn_number=3,
        round_number=2,
    )
    user = prompt.user_prompt
    assert "ALREADY USED" in user
    assert "do not invent replacement numbers" in user
    assert "invent NEW numbers" not in user
    banned = user.split("ALREADY USED", 1)[1].split("(Words from the opponent's LAST verse", 1)[0]
    for spent in ("hamster", "1,732", "disco", "grinder"):
        assert spent in banned
    # words from the opponent's latest verse are never banned: that is how you reply
    assert "sunlit" not in banned and "scripts" not in banned
    # the battle topic itself is never banned
    assert "debugging" not in banned.lower()