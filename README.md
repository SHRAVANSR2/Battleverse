# BattleVerse

Four cartoon robots — **Nova Vex**, **Rook Blaze**, **Baron Byte**, and
**Gizmo Jinx** — trade rap, roast, or debate verses about a topic you pick.
Pick any two to fight: **fighter A always writes with Groq, fighter B always
writes with Gemini**. Every line is spoken aloud by Piper in the fighter's
own voice, and rap battles sit on top of a procedurally generated boom-bap
beat. You vote for a winner, and battles are saved with history, a
leaderboard, rematch links, and a small rivalry memory the robots carry into
the next fight.

- **Backend:** Python 3.11 · FastAPI · SQLAlchemy · SQLite · Alembic
- **Frontend:** React 19 · TypeScript · Vite · Tailwind CSS 4
- **LLMs:** [Groq](https://console.groq.com) (`openai/gpt-oss-120b`) for fighter A and [Gemini](https://ai.google.dev/gemini-api) (`gemini-3.8-flash`, falling back to `gemini-3.1-flash-lite`) for fighter B
- **TTS:** [Piper](https://github.com/OHF-Voice/piper1-gpl) — local, offline, CPU
- **Music:** none recorded — the beat is synthesised live with the Web Audio API

Both `GROQ_API_KEY` and `GEMINI_API_KEY` are required for battles. Each verse
is tagged with its actual provider. If a key is missing, that fighter's turn
fails with a setup message; the app does not substitute scripted verses.

---

## Quick start (Windows PowerShell)

Prerequisites: **Python 3.11+**, **Node 20+**, and ~250 MB of disk for the
four voice models. `ffprobe` is optional (used only by the audio smoke test).

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

### 2. Install the backend (with Groq, Gemini, and Piper)

```powershell
pip install -e "backend[dev,groq,gemini,tts]"
```

### 3. Download the four voices (one time, ~250 MB)

Each robot has its own Piper voice:

| Robot        | Voice model             |
|---|---|
| Nova Vex     | `en_US-kristin-medium`  |
| Rook Blaze   | `en_US-joe-medium`      |
| Baron Byte   | `en_GB-alan-medium`     |
| Gizmo Jinx   | `en_US-amy-medium`      |

```powershell
python -m piper.download_voices en_US-kristin-medium en_US-joe-medium en_GB-alan-medium en_US-amy-medium --download-dir backend\storage\models
```

### 4. Configure

```powershell
Copy-Item .env.example .env
notepad .env      # add GROQ_API_KEY and GEMINI_API_KEY, save, close
```

Get keys at <https://console.groq.com/keys> and
<https://aistudio.google.com/apikey>. `.env` is gitignored and never sent to
the browser. Never share API keys in chat or commit them.

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

Expected: **110 passed**, with the real-Piper and live-LLM tests deselected.

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
npm run test:run      # 44 passed
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
model, token counts, and the parsed verse.

---

## How it works

### Battle flow

1. `POST /api/battles` creates a battle from two character IDs, a topic, and
   a style (`rap`, `roast`, or `debate`); state is `created`.
2. `POST /api/battles/{id}/turn` generates the next verse. The backend decides
   who speaks: **A on odd turns, B on even**, so round `r` is turns `2r-1` and
   `2r`. It flips to `in_progress` on the first turn and to `awaiting_vote`
   after the last.
3. The next verse's prompt includes the topic, both personas, the last three
   verses (so the reply is contextual), a "spent ammo" list banning overused
   words, and up to two rivalry memories.
4. `POST /api/battles/{id}/vote` records one vote per browser and completes
   the battle.
5. `POST /api/battles/{id}/rematch` creates a linked follow-up battle; the
   rivalry summary ("Last time Nova Vex won") is injected into the new
   prompts.

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

For **rap** style, the verse text is re-punctuated before synthesis
(`services/speech_text.py`): commas after bars 1 and 3, full stops after bars
2 and 4, so Piper breathes bar-by-bar instead of reading the verse as one
breathless sentence. Other styles are spoken exactly as written.

Details, engine comparison, and caveats: [docs/TTS.md](docs/TTS.md).

### The beat

Rap battles play over a small procedural boom-bap loop generated entirely in
the browser (`frontend/src/audio/beat.ts` — no audio files). One 16-step Web
Audio scheduler, three profiles:

- **rap** — 90 BPM: kick 0/6/10, snare 4/12, swung 8th hats, 808
  A-A-F-G, Am stab on bars 1 and 3
- **roast** — 72 BPM: kick 0/8, snare 4/12, no hats, no stabs (lazier, meaner)
- **debate** — 60 BPM: kick 0, soft "gavel" thump on 8, sparse hat on 4/12
  (a ticking-clock feel)

The beat loops for the whole battle and starts on the first verse.

### Provider tagging

| Surface | What it shows |
|---|---|
| `/api/health` | Provider assignments and whether each key is configured |
| Every verse | `Groq` or `Gemini` tag next to the author |
| Database | `verses.provider` records the actual provider |

---

## Configuration

All settings live in `.env` (see `.env.example`). Relative paths resolve from
`backend/`.

| Variable | Default | Meaning |
|---|---|---|
| `GROQ_API_KEY` | *(empty)* | Required for fighter A (Groq). |
| `LLM_MODEL` | `openai/gpt-oss-120b` | Groq model ID. Alternative: `openai/gpt-oss-20b`. |
| `GEMINI_API_KEY` | *(empty)* | Required for fighter B (Gemini). |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Primary Gemini model for fighter B. |
| `GEMINI_FALLBACK_MODEL` | `gemini-3.1-flash-lite` | Used if the primary model is unavailable. |
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

When a limit is hit the API returns `LLM_RATE_LIMITED` (429) and the UI
explains it in plain language rather than retrying in a storm. **No paid
billing is configured or enabled by this app.** If a model ID is retired, the
API returns `LLM_MODEL_UNAVAILABLE` telling you to update `LLM_MODEL`.

---

## API reference

Errors always return `{"error": {"code", "message", "request_id"}}`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Status, provider, TTS readiness — never the key |
| `GET` | `/api/characters` | The four built-in robots |
| `GET` | `/api/characters/{id}` | One robot by ID |
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
                   audio_service, audio_storage, battle_queries,
                   speech_text, memory
      providers\llm\   base, groq_adapter, gemini_adapter, demo_writer,
                       registry, errors
      providers\tts\   base, voices, fake, piper_adapter, registry
      scripts\     tts_smoke, groq_smoke, live_check
      seeds\       characters
    storage\      gitignored: battleverse.db, models\, audio\
    tests\        conftest, units, flow, engine edges, gemini adapter,
                  llm registry, roster and style, verse quality rules,
                  tts resilience, real\ (piper, opt-in)
  frontend\
    playwright.config.ts  e2e\arena.spec.ts
    src\
      pages\        Home, BattleSetup, BattleArena, Results, History,
                    Leaderboard, NotFound
      components\   layout, ui, battle (SpeechBubble, BattleStage,
                    VotingPanel), audio, character (inline SVG robots)
      audio\        AudioProvider, audioMachine (pure reducer), beat
      hooks\        useBattle, useHealth, useVoterKey, useDocumentTitle,
                    useRapBeat
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
silently fall back to anything else; fix or remove the key.

**No sound in the browser** — click **Play** once. Browsers block autoplay
until a gesture; the app shows a banner and retries after your tap. The beat
starts with the first verse for the same reason.

**`npm install` peer conflicts** — this repo pins exact versions and ships a
`package-lock.json`. Use `npm ci` rather than mixing versions.

---

## Known limitations

- One uvicorn worker only. Scaling beyond a single process would need a shared
  lock (the per-battle lock is in-process); the CAS and unique index still hold.
- Overall vote only — no per-round scoring, and no AI judge (by design).
- English (`en_US`/`en_GB`) voices only.
- Voting uses per-browser local storage keys, which is adequate for a local
  game but not a defence against determined ballot stuffing.
- The beat is a fixed loop per style — it does not respond to the verse
  content (by design, to keep the frontend free of audio assets).
