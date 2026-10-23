# BattleVerse

Two cartoon robots, **Nova Vex** and **Rook Blaze**, trade rap, roast, or debate
verses about a topic you pick. Every line is written by an LLM (Groq) and then
**spoken aloud in two genuinely different real voices** generated locally by
Piper. You vote for a winner, and battles are saved with history, a leaderboard,
rematch links, and a small rivalry memory that the robots carry into the next
fight.

- **Backend:** Python 3.11 · FastAPI · SQLAlchemy · SQLite · Alembic
- **Frontend:** React 19 · TypeScript · Vite · Tailwind CSS 4
- **LLM:** [Groq](https://console.groq.com) (`openai/gpt-oss-120b`) — free tier
- **TTS:** [Piper](https://github.com/OHF-Voice/piper1-gpl) — local, offline, CPU

> **Demo Mode.** With no `GROQ_API_KEY`, BattleVerse still runs, but a clearly
> labelled scripted writer produces the verses. Every such verse is tagged
> `demo` in the UI and `provider=demo` in the database. Scripted output is
> **never** presented as AI-generated.

---

## Quick start (Windows PowerShell)

Prerequisites: **Python 3.11+**, **Node 20+**, and ~130 MB of disk for the voice
models. `ffprobe` is optional (used only by the audio smoke test).

### 1. Clone and create the environment

```powershell
cd D:\ClaudeCodeTest
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks the activation script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Install the backend (with Groq and Piper)

```powershell
pip install -e "backend[dev,groq,tts]"
```

### 3. Download the two voices (one time, ~122 MB)

```powershell
python -m piper.download_voices en_US-joe-medium en_US-kristin-medium --download-dir backend\storage\models
```

### 4. Configure

```powershell
Copy-Item .env.example .env
notepad .env      # paste your GROQ_API_KEY, save, close
```

Get a free key at <https://console.groq.com/keys>. Leave `GROQ_API_KEY` empty to
use the labelled Demo Mode. `.env` is gitignored and never sent to the browser.

### 5. Create and seed the database

```powershell
cd backend
python -m app.cli init-db
cd ..
```

### 6. Run

Terminal 1 (backend):

```powershell
cd D:\ClaudeCodeTest\backend
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Terminal 2 (frontend):

```powershell
cd D:\ClaudeCodeTest\frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

> Vite binds `localhost` (IPv6 `::1`) on Windows. Use `localhost`, not
> `127.0.0.1`, in the browser — the proxy handles the backend either way.

---

## Verify it actually works

These are the checks the project was built against. Run them in order.

### Backend tests (offline, no models, no network)

```powershell
cd D:\ClaudeCodeTest
.\.venv\Scripts\Activate.ps1
pytest backend/tests -q
```

Expected: **63 passed**, with the real-Piper and live-Groq tests deselected.

### Real speech, no browser involved

```powershell
python -m app.scripts.tts_smoke --voices-dir backend\storage\models --out backend\storage\audio\smoke
```

Fails loudly unless it writes valid 22 050 Hz 16-bit mono WAV files over 10 KB
for **both** voices. Prints bytes, duration, synthesis time, peak RSS, and an
`ffprobe` summary.

### Real Piper through pytest

```powershell
pytest backend/tests/real -m piper
```

Expected: **3 passed**. Skipped automatically if the models are absent.

### Frontend unit tests and build

```powershell
cd frontend
npm run test:run      # 26 passed
npm run build         # tsc -b && vite build
```

### End-to-end in a real browser

With the backend **already running** on port 8000:

```powershell
cd D:\ClaudeCodeTest\frontend
npx playwright test
```

Drives installed Chrome (no browser download). Creates a battle, generates two
turns, plays a real synthesized verse, checks the Speaking highlight, pauses,
resumes, replays, mutes, changes volume, votes, and rematches — asserting that
replay never adds a verse or calls the turn endpoint. Screenshots land in
`frontend/e2e-artifacts/screenshots/`.

### Full live API walkthrough

With the backend running:

```powershell
cd D:\ClaudeCodeTest\backend
..\.venv\Scripts\python.exe -m app.scripts.live_check
```

Creates a battle, generates turns, synthesizes real audio, downloads and
validates it, proves the cache and no-new-verse behaviour, votes, and rematches.

### Live Groq check (needs a key)

```powershell
cd D:\ClaudeCodeTest\backend
..\.venv\Scripts\python.exe -m app.scripts.groq_smoke
```

Makes one real API call with the production adapter and prompt, then prints the
model, token counts, and the parsed verse. It refuses to run in Demo Mode.

---

## How it works

### Battle flow

1. `POST /api/battles` creates a battle (`created`).
2. `POST /api/battles/{id}/turn` generates the next verse. The backend decides
   who speaks: **A on odd turns, B on even**, so round `r` is turns `2r-1` and
   `2r`. It flips to `in_progress` on the first turn and to `awaiting_vote`
   after the last.
3. The next verse's prompt includes the topic, both personas, the last three
   verses (so the reply is contextual), and up to two rivalry memories.
4. `POST /api/battles/{id}/vote` records one vote per browser and completes the
   battle.
5. `POST /api/battles/{id}/rematch` creates a linked follow-up battle; the
   rivalry summary is injected into the new prompts.

### Duplicate turns are prevented four ways

1. `expected_turn_number` makes a retry **idempotent** — replaying an already
   generated turn returns it with `created: false` instead of generating again.
2. A per-battle `asyncio.Lock` serializes concurrent requests (`TURN_BUSY`).
3. A compare-and-swap `UPDATE ... WHERE state_version = ? AND next_turn_number = ?`
   rejects stale writes.
4. `UNIQUE(battle_id, turn_number)` is the final database guard.

A provider failure changes nothing: no verse, no turn advance, no status
change. The client retries the same turn number.

### Audio pipeline

`POST /api/verses/{id}/audio` → cache lookup → Piper synthesis **outside any
database transaction** → WAV validation → atomic write to
`backend/storage/audio/YYYY/MM/<uuid4>.wav` → asset row → response containing
`/api/audio/{audio_id}`.

- Cache key: `sha256(v1 | provider | voice | settings | normalized text)`.
- Identical text reuses the stored file across verses.
- The API never returns a filesystem path; serving rejects traversal.
- A missing model yields **`TTS_UNAVAILABLE`** while the verse and turn pointer
  survive, and pressing Play again retries.
- Filenames are opaque and content-addressed, so responses are served with
  `Cache-Control: immutable`.

Details, engine comparison, and caveats: [docs/TTS.md](docs/TTS.md).

### Demo Mode honesty

| Surface | What it shows |
|---|---|
| `/api/health` | `llm_provider: "demo"`, `demo_mode: true` |
| Nav bar | Persistent **Demo Mode** chip |
| Every verse | A `demo` tag next to the author |
| Database | `verses.provider = 'demo'` |
| Result page | "demo line (scripted, not AI-generated)" |

Tests assert the tag appears for `provider="demo"` and is absent for
`provider="groq"`.

---

## Configuration

All settings live in `.env` (see `.env.example`). Relative paths resolve from
`backend/`.

| Variable | Default | Meaning |
|---|---|---|
| `GROQ_API_KEY` | *(empty)* | Empty → Demo Mode. Present → Groq generates verses. |
| `LLM_MODEL` | `openai/gpt-oss-120b` | Groq model ID. Alternative: `openai/gpt-oss-20b`. |
| `LLM_TIMEOUT_SECONDS` | `45` | Per-request timeout |
| `LLM_MAX_RETRIES` | `1` | App-level retries (clamped to ≤1; the SDK's own retries are off) |
| `LLM_TEMPERATURE` | `0.9` | Sampling temperature |
| `LLM_MAX_TOKENS` | `320` | Response cap |
| `TTS_PROVIDER` | `piper` | `piper` (real) or `fake` (tests only) |
| `TTS_VOICES_DIR` | `./storage/models` | Where voice `.onnx` files live |
| `TTS_TIMEOUT_SECONDS` | `60` | Includes first-time model load |
| `TTS_MAX_TEXT_CHARS` | `800` | Rejects longer verses |
| `AUDIO_STORAGE_DIR` | `./storage/audio` | Generated WAV root |
| `DATABASE_URL` | `sqlite+pysqlite:///./storage/battleverse.db` | SQLite file |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Direct-API origins |
| `LOG_LEVEL` | `INFO` | Logging level |

### Groq free tier

Per Groq's published limits for the `gpt-oss` models on the free tier: roughly
**30 requests/minute, 1 000 requests/day, 8 000 tokens/minute**. A six-turn
battle is six requests with a small prompt, so it fits comfortably; starting
several battles at once will not. These are Groq's numbers and may change.

When a limit is hit the API returns `LLM_RATE_LIMITED` (429) and the UI explains
it in plain language rather than retrying in a storm. **No paid billing is
configured or enabled by this app.** If a model ID is retired, the API returns
`LLM_MODEL_UNAVAILABLE` telling you to update `LLM_MODEL`.

---

## API reference

Errors always return `{"error": {"code", "message", "request_id"}}`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Status, provider, demo flag, TTS readiness — never the key |
| `GET` | `/api/characters` | The two built-in robots |
| `POST` | `/api/battles` | Create a battle |
| `GET` | `/api/battles` | List battles (`?status=&limit=`) |
| `GET` | `/api/battles/{id}` | Detail with verses, audio, and result |
| `POST` | `/api/battles/{id}/turn` | Generate the next verse |
| `POST` | `/api/battles/{id}/vote` | Cast a vote |
| `GET` | `/api/battles/{id}/result` | Tallies, winner, highlight line |
| `POST` | `/api/battles/{id}/rematch` | Create a linked rematch |
| `POST` | `/api/verses/{id}/audio` | Synthesize (or fetch cached) verse audio |
| `GET` | `/api/audio/{id}` | Serve WAV bytes (Range supported) |
| `GET` | `/api/tts/voices` | Configured voices and availability |
| `GET` | `/api/tts/health` | Provider, voices found, missing models |
| `POST` | `/api/tts/preview` | Preview a voice with short text |
| `GET` | `/api/history` | Completed battles |
| `GET` | `/api/leaderboard` | Wins, battles, win rate per robot |

Interactive docs while the backend runs: <http://127.0.0.1:8000/docs>.

---

## Project layout

```
D:\ClaudeCodeTest\
  README.md  design.md  .env.example  .gitignore  .gitattributes
  docs\TTS.md  docs\THIRD_PARTY_AND_LICENSES.md
  backend\
    pyproject.toml  alembic.ini  alembic\versions\0001_initial_schema.py
    app\
      main.py  cli.py
      core\        config, db, errors, logging, request context
      models\      character, battle, verse, audio_asset, vote, memory
      schemas\     pydantic wire types
      api\         routes: health, characters, battles, audio, tts
      services\    battle_engine, prompt_builder, verse_validator,
                   audio_service, audio_storage, battle_queries
      providers\llm\   base, demo_writer, groq_adapter, registry, errors
      providers\tts\   base, voices, fake, piper_adapter, registry
      scripts\     tts_smoke, groq_smoke, live_check
      seeds\       characters
    storage\      gitignored: battleverse.db, models\, audio\
    tests\        conftest, units, flow, engine edges, groq adapter,
                  tts resilience, demo writer, real\ (piper, opt-in)
  frontend\
    playwright.config.ts  e2e\arena.spec.ts
    src\
      pages\        Home, BattleSetup, BattleArena, Results, History,
                    Leaderboard, NotFound
      components\   layout, ui, battle, audio, character (inline SVG robots)
      audio\        AudioProvider, audioMachine (pure reducer)
      hooks\        useBattle, useHealth, useVoterKey, useDocumentTitle
      services\     client, battles, audio, system
      test\         setup, fixtures
```

---

## Troubleshooting

**`database_ready: false` on `/api/health`** — run `cd backend; python -m app.cli init-db`.

**`TTS_UNAVAILABLE` / voices_found 0** — download the models (step 3). Check
`Invoke-RestMethod http://127.0.0.1:8000/api/tts/health` for the missing names.

**First line takes ~12 s to speak** — that is the voice model loading. Later
lines are much faster; the audio is cached per verse afterwards.

**`LLM_AUTH_FAILED`** — the key in `.env` is wrong or revoked. The app does not
silently fall back to Demo Mode; fix or remove the key.

**No sound in the browser** — click **Play** once. Browsers block autoplay until
a gesture; the app shows a banner and retries after your tap.

**`npm install` peer conflicts** — this repo pins exact versions and ships a
`package-lock.json`. Use `npm ci` rather than mixing versions.

---

## Known limitations

- **Live Groq generation could not be verified in this build environment**
  because no API key was available. Everything else in the Groq path is covered
  by tests with a stubbed SDK client. To verify for real, put a key in `.env`
  and run `python -m app.scripts.groq_smoke`.
- One uvicorn worker only. Scaling beyond a single process would need a shared
  lock (the per-battle lock is in-process); the CAS and unique index still hold.
- Overall vote only — no per-round scoring, and no AI judge (by design).
- English (`en_US`) voices only.
- Voting uses per-browser local storage keys, which is adequate for a local game
  but not a defence against determined ballot stuffing.
