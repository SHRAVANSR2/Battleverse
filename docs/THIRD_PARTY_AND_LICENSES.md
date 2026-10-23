# Third-party components and licences

BattleVerse is a local-first application. Nothing here is vendored into the
repository; all of it is installed by `pip` / `npm` at setup time.

## Runtime dependencies

### Backend (Python)

| Package | Version | Licence | Notes |
|---|---|---|---|
| fastapi | 0.161.1 | MIT | Web framework |
| starlette | 1.9.0 | BSD-3-Clause | ASGI toolkit (FastAPI dependency) |
| uvicorn | 0.54.0 | BSD-3-Clause | ASGI server |
| sqlalchemy | 2.1.6 | MIT | ORM |
| alembic | 1.20.1 | MIT | Migrations |
| pydantic | 2.14.1 | MIT | Validation |
| pydantic-settings | 2.16.1 | MIT | Env config |
| python-dotenv | 1.2.1 | BSD-3-Clause | `.env` loading |
| **groq** | **1.7.0** | **Apache-2.0** | Optional extra `[groq]` — the LLM client |
| **piper-tts** | **1.8.0** | **GPL-3.0-or-later** | Optional extra `[tts]` — the TTS engine |
| onnxruntime | 1.x | MIT | Piper dependency |
| pathvalidate | 3.x | MIT | Piper dependency |
| pytest | 9.1.1 | MIT | Dev only |
| httpx | 0.28.1 | BSD-3-Clause | Dev/test only |

### Frontend (npm)

| Package | Version | Licence |
|---|---|---|
| react / react-dom | 19.3.1 | MIT |
| react-router-dom | 7.18.4 | MIT |
| vite | 7.3.7 | MIT |
| @vitejs/plugin-react | 5.2.0 | MIT |
| typescript | 5.9.3 | Apache-2.0 |
| tailwindcss / @tailwindcss/vite | 4.3.3 | MIT |
| vitest | 5.0.5 | MIT |
| jsdom | 30.1.3 | MIT |
| @testing-library/* | 16.3.3 / 7.0.1 / 14.6.8 | MIT |
| @playwright/test | 1.64.1 | Apache-2.0 |

## Voice models (downloaded, not committed)

| Voice | Dataset source | Licence |
|---|---|---|
| `en_US-kristin-medium` | LibriVox recordings | Public domain |
| `en_US-joe-medium` | Piper `joe` dataset | CC0 |

Downloaded from the `rhasspy/piper-voices` repository on Hugging Face. Verify
current licensing terms there before redistributing the model files themselves.

Voices deliberately **not** used, because their datasets restrict commercial use:

- `en_US-ryan-*`, `en_US-hfc_female-medium`, `en_US-hfc_male-medium` — CC BY-NC-SA
- `en_US-lessac-*` — Blizzard 2013 licence

## Interpreting the Piper licence (GPL-3.0-or-later)

`piper-tts` is GPL-3.0-or-later. Consequences for this project:

- It is an **optional install extra** (`pip install -e "backend[tts]"`). It is
  not copied into the repository, not bundled into any artifact, and not linked
  into a distributed binary.
- The **WAV files Piper generates are output, not a derivative work** of the
  engine. They are your content, distributed under whatever terms you choose.
- If you fork BattleVerse and ship it as a closed product **with `piper-tts`
  bundled in**, you would need to comply with the GPL. Keeping it as an
  install-time optional dependency, as this repository does, avoids that.
- If you need a permissively licensed engine, swap the adapter: the
  `TTSProvider` interface in `backend/app/providers/tts/base.py` is the only
  place to implement. Nothing else in the app references Piper.

## Groq

The Groq API is a hosted service, not distributed software. Verse requests go to
`api.groq.com` when `GROQ_API_KEY` is set. The free tier's rate limits apply and
are documented in the README. No paid billing is enabled by this application.

## Fonts, images, audio assets

- No web fonts are downloaded; the UI uses the system UI font stack.
- Both robot avatars are hand-written inline SVG in
  `frontend/src/components/character/RobotAvatar.tsx` — no third-party art.
- No recorded audio is shipped. Every WAV is generated locally at runtime.
