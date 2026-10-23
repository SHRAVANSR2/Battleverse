"""A TTS failure must never damage the text or the battle state.

Covers the release gate: "renaming a model file makes TTS fail while the verse
and turn pointer survive, and Retry succeeds after restore."
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.errors import TTSSynthesisError, TTSUnavailableError
from app.providers.tts.base import AudioResult, Voice
from app.providers.tts.fake import FakeTTSProvider


class FlakyTTSProvider(FakeTTSProvider):
    """Delegates to the fake provider until ``fail_with`` is set."""

    def __init__(self) -> None:
        super().__init__()
        self.fail_with: Exception | None = TTSUnavailableError(
            "Voice model 'en_US-kristin-medium.onnx' is missing."
        )

    async def synthesize(self, text: str, voice_id: str) -> AudioResult:
        if self.fail_with is not None:
            raise self.fail_with
        return await super().synthesize(text, voice_id)


def _started_battle(client: TestClient, characters: list[dict]) -> tuple[str, str]:
    battle = client.post(
        "/api/battles",
        json={
            "fighter_a_id": characters[0]["id"],
            "fighter_b_id": characters[1]["id"],
            "topic": "best antenna polish",
            "style": "rap",
            "intensity": "playful",
            "round_count": 2,
            "playback_mode": "manual",
        },
    ).json()
    turn = client.post(
        f"/api/battles/{battle['id']}/turn", json={"expected_turn_number": 1}
    )
    assert turn.status_code == 200, turn.text
    return battle["id"], turn.json()["verse"]["id"]


def test_tts_failure_leaves_verse_and_turn_intact_then_retry_succeeds(app, client, characters):
    flaky = FlakyTTSProvider()
    app.state.tts = flaky

    battle_id, verse_id = _started_battle(client, characters)
    before = client.get(f"/api/battles/{battle_id}").json()
    verse_before = before["verses"][0]

    response = client.post(f"/api/verses/{verse_id}/audio", json={})
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "TTS_UNAVAILABLE"

    after = client.get(f"/api/battles/{battle_id}").json()
    assert after["next_turn_number"] == before["next_turn_number"]
    assert after["state_version"] == before["state_version"]
    assert after["status"] == "in_progress"
    assert len(after["verses"]) == 1
    assert after["verses"][0]["verse_text"] == verse_before["verse_text"]
    assert after["verses"][0]["audio"] is None or after["verses"][0]["audio"]["status"] == "failed"

    # The turn pointer did not advance: the very next turn is still #2.
    turn_two = client.post(
        f"/api/battles/{battle_id}/turn", json={"expected_turn_number": 2}
    )
    assert turn_two.status_code == 200, turn_two.text

    # Restore the engine and retry the same verse: no new turn appears.
    flaky.fail_with = None
    retry = client.post(f"/api/verses/{verse_id}/audio", json={})
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "ready"
    assert retry.json()["size_bytes"] > 1000

    final = client.get(f"/api/battles/{battle_id}").json()
    assert len(final["verses"]) == 2  # the failed audio did not add a verse
    media = client.get(retry.json()["url"])
    assert media.status_code == 200
    assert media.content[:4] == b"RIFF"


def test_synthesis_error_also_preserves_state(app, client, characters):
    flaky = FlakyTTSProvider()
    flaky.fail_with = TTSSynthesisError("The speech engine returned an invalid audio file.")
    app.state.tts = flaky

    battle_id, verse_id = _started_battle(client, characters)
    response = client.post(f"/api/verses/{verse_id}/audio", json={})
    assert response.status_code == 502, response.text
    assert response.json()["error"]["code"] == "TTS_SYNTHESIS_FAILED"

    detail = client.get(f"/api/battles/{battle_id}").json()
    assert detail["verses"][0]["verse_text"].strip()
    assert detail["next_turn_number"] == 2


def test_invalid_voice_is_rejected_before_synthesis(app, client, characters):
    battle_id, verse_id = _started_battle(client, characters)
    # Swap in a provider whose allowlist does not contain the character's voice.
    app.state.tts = _EmptyVoiceProvider()
    response = client.post(f"/api/verses/{verse_id}/audio", json={})
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "INVALID_VOICE"
    assert client.get(f"/api/battles/{battle_id}").json()["next_turn_number"] == 2


class _EmptyVoiceProvider(FakeTTSProvider):
    def list_voices(self) -> list[Voice]:
        return []
