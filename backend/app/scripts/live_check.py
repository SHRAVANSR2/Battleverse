"""Live end-to-end check against a running backend.

    python -m app.scripts.live_check [--base http://127.0.0.1:8000]

Creates a battle, generates a few turns, synthesizes real audio for each verse
(Piper when configured), downloads it, verifies the WAV, checks that replaying
audio does not create a verse, votes, and prints the result. Exits non-zero on
any failed assertion.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.error
import urllib.request
import wave

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "ok  " if condition else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}")
    if not condition:
        FAILURES.append(label)


class Api:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")

    def call(self, method: str, path: str, body: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            f"{self.base}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                raw = response.read()
                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    return response.status, json.loads(raw), response.headers
                return response.status, raw, response.headers
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"raw": raw[:200].decode("utf-8", "replace")}
            return exc.code, payload, exc.headers

    def get(self, path):
        return self.call("GET", path)

    def post(self, path, body=None):
        return self.call("POST", path, body if body is not None else {})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--turns", type=int, default=2)
    args = parser.parse_args(argv)
    api = Api(args.base)

    print("== health ==")
    status, health, _ = api.get("/api/health")
    check("health 200", status == 200, str(status))
    check("database ready", health.get("database_ready") is True)
    print(f"   llm={health.get('llm_provider')} demo={health.get('demo_mode')} "
          f"tts={health.get('tts_provider')} tts_ready={health.get('tts_ready')}")
    if health.get("llm_provider") == "demo":
        print("   NOTE: Demo Mode — verses are scripted, not AI-generated.")

    print("\n== characters ==")
    _, characters, _ = api.get("/api/characters")
    check("two built-ins", len(characters) >= 2, f"{len(characters)} found")
    a, b = characters[0], characters[1]
    print(f"   {a['name']} ({a['voice_id']}) vs {b['name']} ({b['voice_id']})")

    print("\n== create battle ==")
    status, battle, _ = api.post(
        "/api/battles",
        {
            "fighter_a_id": a["id"],
            "fighter_b_id": b["id"],
            "topic": "who has the best antenna",
            "style": "rap",
            "intensity": "playful",
            "round_count": 2,
            "playback_mode": "manual",
        },
    )
    check("201 created", status == 201, str(status))
    battle_id = battle["id"]
    print(f"   battle {battle_id} total_turns={battle['total_turns']}")

    print("\n== turns ==")
    for expected in range(1, min(args.turns, battle["total_turns"]) + 1):
        status, turn, _ = api.post(
            f"/api/battles/{battle_id}/turn", {"expected_turn_number": expected}
        )
        ok = status == 200 and turn.get("verse", {}).get("turn_number") == expected
        check(f"turn {expected} generated", ok, str(status))
        if ok:
            verse = turn["verse"]
            first_line = verse["verse_text"].split("\n")[0]
            print(f"   [{verse['character_name']}] {first_line}")
            print(f"      provider={verse['provider']} demo={verse['is_demo']}")

    status, detail, _ = api.get(f"/api/battles/{battle_id}")
    verses = detail["verses"]
    check("verses persisted", len(verses) == min(args.turns, battle["total_turns"]),
          f"{len(verses)} verses")

    print("\n== audio (real synthesis) ==")
    for verse in verses[:2]:
        status, audio, _ = api.post(f"/api/verses/{verse['id']}/audio")
        ok = status == 200 and audio.get("status") == "ready"
        check(f"audio for turn {verse['turn_number']}", ok, str(status))
        if not ok:
            print(f"      {audio}")
            continue
        print(f"      {audio['bytes'] if 'bytes' in audio else audio['size_bytes']:,} bytes, "
              f"{audio['duration_ms']} ms, voice={audio['voice_id']}")

        media_status, data, headers = api.get(audio["url"])
        check("audio url serves bytes", media_status == 200, str(media_status))
        if media_status == 200:
            check("RIFF/WAVE header", data[:4] == b"RIFF" and data[8:12] == b"WAVE")
            with wave.open(io.BytesIO(data), "rb") as wav_file:
                seconds = wav_file.getnframes() / wav_file.getframerate()
            check("audible duration", seconds > 0.5, f"{seconds:.2f}s")
            check("content-type", "audio/wav" in headers.get("content-type", ""),
                  headers.get("content-type", ""))

        # Cached second request must not re-synthesize.
        _, again, _ = api.post(f"/api/verses/{verse['id']}/audio")
        check("second request is cached", again.get("cached") is True)

    status, detail_after, _ = api.get(f"/api/battles/{battle_id}")
    check("audio requests created no verses", len(detail_after["verses"]) == len(verses),
          f"{len(detail_after['verses'])} verses")

    print("\n== finish + vote ==")
    # Play out the remaining turns.
    current = len(detail_after["verses"])
    total = detail_after["total_turns"]
    while current < total:
        status, _, _ = api.post(
            f"/api/battles/{battle_id}/turn", {"expected_turn_number": current + 1}
        )
        if status != 200:
            check(f"turn {current + 1}", False, str(status))
            break
        current += 1

    _, state, _ = api.get(f"/api/battles/{battle_id}")
    check("battle awaiting vote", state["status"] == "awaiting_vote", state["status"])

    status, vote, _ = api.post(
        f"/api/battles/{battle_id}/vote",
        {"winner_character_id": a["id"], "voter_key": "live-check-0001"},
    )
    check("vote accepted", status == 200, str(status))
    if status == 200:
        print(f"   winner: {vote['result']['winner']['name']} "
              f"({vote['result']['vote_count']} vote)")

    print("\n== history / rematch ==")
    _, history, _ = api.get("/api/history")
    check("battle in history", any(item["id"] == battle_id for item in history))
    status, rematch, _ = api.post(f"/api/battles/{battle_id}/rematch")
    check("rematch created", status == 201, str(status))
    if status == 201:
        check("rematch links previous", rematch["previous_battle_id"] == battle_id)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}", file=sys.stderr)
        return 1
    print("All live checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())