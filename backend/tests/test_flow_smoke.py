"""End-to-end smoke: create -> turns -> audio -> vote -> result -> rematch."""

from __future__ import annotations


def _create_battle(client, characters, rounds: int = 2):
    a, b = characters[0], characters[1]
    response = client.post(
        "/api/battles",
        json={
            "fighter_a_id": a["id"],
            "fighter_b_id": b["id"],
            "topic": "who has the best antenna",
            "style": "rap",
            "intensity": "playful",
            "round_count": rounds,
            "playback_mode": "manual",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_health(client):
    body = client.get("/api/health").json()
    assert body["database_ready"] is True
    assert body["demo_mode"] is True
    assert body["llm_provider"] == "demo"
    assert "groq_api_key" not in str(body).lower()


def test_full_flow(client, characters):
    battle = _create_battle(client, characters, rounds=2)
    battle_id = battle["id"]
    assert battle["total_turns"] == 4

    for expected in range(1, 5):
        response = client.post(
            f"/api/battles/{battle_id}/turn", json={"expected_turn_number": expected}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["created"] is True
        assert body["verse"]["turn_number"] == expected
        assert body["verse"]["is_demo"] is True
        assert body["verse"]["provider"] == "demo"
        assert body["verse"]["round_number"] == (expected - 1) // 2 + 1

    detail = client.get(f"/api/battles/{battle_id}").json()
    assert detail["status"] == "awaiting_vote"
    assert len(detail["verses"]) == 4
    # Alternation: A, B, A, B
    assert [v["character_id"] for v in detail["verses"]] == [
        characters[0]["id"],
        characters[1]["id"],
        characters[0]["id"],
        characters[1]["id"],
    ]

    # Idempotent replay must not create a second verse.
    replay = client.post(
        f"/api/battles/{battle_id}/turn", json={"expected_turn_number": 4}
    )
    assert replay.status_code == 200
    assert replay.json()["created"] is False
    assert len(client.get(f"/api/battles/{battle_id}").json()["verses"]) == 4

    verse_id = detail["verses"][0]["id"]
    audio = client.post(f"/api/verses/{verse_id}/audio", json={})
    assert audio.status_code == 200, audio.text
    audio_body = audio.json()
    assert audio_body["status"] == "ready"
    assert audio_body["size_bytes"] > 1000

    media = client.get(audio_body["url"])
    assert media.status_code == 200
    assert media.headers["content-type"].startswith("audio/wav")
    assert media.content[:4] == b"RIFF"

    again = client.post(f"/api/verses/{verse_id}/audio", json={})
    assert again.json()["cached"] is True

    vote = client.post(
        f"/api/battles/{battle_id}/vote",
        json={"winner_character_id": characters[0]["id"], "voter_key": "tester-0001"},
    )
    assert vote.status_code == 200, vote.text
    vote_body = vote.json()
    assert vote_body["battle"]["status"] == "completed"
    assert vote_body["result"]["winner"]["name"] == characters[0]["name"]

    result = client.get(f"/api/battles/{battle_id}/result").json()
    assert result["is_draw"] is False
    assert result["vote_count"] == 1
    assert sum(f["votes"] for f in result["fighters"]) == 1

    history = client.get("/api/history").json()
    assert any(item["id"] == battle_id for item in history)

    rematch = client.post(f"/api/battles/{battle_id}/rematch")
    assert rematch.status_code == 201
    assert rematch.json()["previous_battle_id"] == battle_id

    leaderboard = client.get("/api/leaderboard").json()
    assert len(leaderboard) == 2
    assert any(row["wins"] >= 1 for row in leaderboard)


def test_turns_after_finish_are_rejected(client, characters):
    battle = _create_battle(client, characters, rounds=1)
    battle_id = battle["id"]
    for expected in (1, 2):
        assert (
            client.post(
                f"/api/battles/{battle_id}/turn", json={"expected_turn_number": expected}
            ).status_code
            == 200
        )
    late = client.post(f"/api/battles/{battle_id}/turn", json={})
    assert late.status_code == 409
    assert late.json()["error"]["code"] == "BATTLE_NOT_IN_PROGRESS"