"""Pure-unit coverage: turn math, validator, cache keys, storage safety."""

from __future__ import annotations

import pytest

from app.core.errors import AudioFileMissingError, ProviderInvalidOutputError
from app.services import turn_math
from app.services.audio_service import build_cache_key, normalize_text
from app.services.audio_storage import AudioStorage
from app.services.verse_validator import parse_verse


class TestTurnMath:
    @pytest.mark.parametrize("turn,expected", [(1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (10, 5)])
    def test_round_for_turn(self, turn, expected):
        assert turn_math.round_for_turn(turn) == expected

    @pytest.mark.parametrize("turn,is_a", [(1, True), (2, False), (3, True), (4, False)])
    def test_speaker_alternates(self, turn, is_a):
        assert turn_math.speaker_is_a(turn) is is_a

    def test_total_turns(self):
        assert turn_math.total_turns(3) == 6
        assert turn_math.total_turns(1) == 2

    def test_final_turn(self):
        assert turn_math.is_final_turn(6, 3) is True
        assert turn_math.is_final_turn(5, 3) is False

    def test_rejects_zero(self):
        with pytest.raises(ValueError):
            turn_math.round_for_turn(0)


class TestVerseValidator:
    def test_json_payload(self):
        parsed = parse_verse(
            '{"verse_text": "First line here\\nSecond line here", "line_count": 2, '
            '"callback_reference": "spark"}'
        )
        assert parsed.line_count == 2
        assert parsed.verse_text == "First line here\nSecond line here"
        assert parsed.callback_reference == "spark"

    def test_markdown_fenced_json(self):
        raw = '```json\n{"verse_text": "A line about robots\\nAnother line here"}\n```'
        parsed = parse_verse(raw)
        assert "Another line" in parsed.verse_text

    def test_plain_text(self):
        parsed = parse_verse("First plain line\nSecond plain line")
        assert parsed.line_count == 2

    def test_strips_bullets_stage_directions_emoji(self):
        parsed = parse_verse("1. (laughs) Hello there friend 🎤\n- And a second line, folks")
        assert "(laughs)" not in parsed.verse_text
        assert "🎤" not in parsed.verse_text
        assert not parsed.verse_text.startswith("-")

    def test_too_few_lines_rejected(self):
        with pytest.raises(ProviderInvalidOutputError):
            parse_verse("just one line")

    def test_empty_rejected(self):
        with pytest.raises(ProviderInvalidOutputError):
            parse_verse("   ")

    def test_json_without_verse_text_rejected(self):
        with pytest.raises(ProviderInvalidOutputError):
            parse_verse('{"lines": ["a", "b"]}')


class TestAudioCacheKey:
    def test_deterministic(self):
        first = build_cache_key("piper", "en_US-joe-medium", "rate=1", "Hello there")
        second = build_cache_key("piper", "en_US-joe-medium", "rate=1", "  hello   THERE ")
        assert first == second

    def test_varies_by_voice_and_provider(self):
        base = build_cache_key("piper", "a", "s", "text")
        assert base != build_cache_key("piper", "b", "s", "text")
        assert base != build_cache_key("fake", "a", "s", "text")
        assert base != build_cache_key("piper", "a", "s2", "text")

    def test_normalize(self):
        assert normalize_text("  A \n B ") == "a b"


class TestAudioStorage:
    def test_write_and_resolve(self, tmp_path):
        storage = AudioStorage(tmp_path)
        key, size = storage.write(b"RIFF" + b"\x00" * 100)
        assert size == 104
        assert storage.exists(key)
        assert storage.resolve(key).is_relative_to(tmp_path.resolve())

    def test_rejects_traversal(self, tmp_path):
        storage = AudioStorage(tmp_path / "audio")
        for key in ("../escape.wav", "../../etc/passwd", "a/../../b.wav"):
            with pytest.raises(AudioFileMissingError):
                storage.resolve(key)

    def test_rejects_absolute(self, tmp_path):
        storage = AudioStorage(tmp_path / "audio")
        with pytest.raises(AudioFileMissingError):
            storage.resolve(str(tmp_path / "elsewhere.wav"))

    def test_empty_data_rejected(self, tmp_path):
        from app.core.errors import TTSSynthesisError

        storage = AudioStorage(tmp_path)
        with pytest.raises(TTSSynthesisError):
            storage.write(b"")