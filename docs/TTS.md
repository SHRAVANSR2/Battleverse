# Text-to-speech in BattleVerse

BattleVerse speaks every verse aloud using **real local neural speech** — no
browser `speechSynthesis`, no pre-recorded samples, no placeholder audio. The
engine is **Piper** (`piper-tts`), which runs offline on CPU.

## Engine choice

| Candidate | Verdict | Why |
|---|---|---|
| **Piper** (`piper-tts` 1.8.0) | **Chosen** | ~63 MB per voice, ONNX Runtime, no PyTorch, 22 050 Hz 16-bit mono WAV, embeds espeak-ng so there is nothing else to install. Verified on this machine. |
| Kokoro (`kokoro`) | Rejected | Pulls `torch` (~2 GB+) plus `transformers`; too heavy for an 8 GB machine and a big install for a browser game. |
| `kokoro-onnx` | Rejected | Avoids PyTorch, but needs `espeakng-loader` + `phonemizer` and a ~300 MB model — a more fragile install than a 63 MB Piper voice. |
| Windows SAPI / `pyttsx3` | Rejected | Robot-voiced system speech varies per machine and cannot give two consistent, distinct character voices. |
| Browser `speechSynthesis` | Rejected | Not generated audio; quality and voices vary by browser/OS, and the design explicitly requires real generated files. |

### Verified on this machine

| Check | Result |
|---|---|
| Kristin, 60-char line | 375 340 bytes, 8.51 s, `pcm_s16le` 22 050 Hz mono, ~12.7 s synthesis |
| Joe, 45-char line | 203 308 bytes, 4.61 s, `pcm_s16le` 22 050 Hz mono, ~11.0 s synthesis |
| Peak RSS during both | ~394 MB |

Synthesis is roughly real-time or a little faster on this CPU; the first call in
a process is slower because the voice model has to load.

## Voices

| Character | Voice | Source | Licence |
|---|---|---|---|
| Nova Vex (mint, chirpy) | `en_US-kristin-medium` | LibriVox recordings | Public domain |
| Rook Blaze (coral, deadpan) | `en_US-joe-medium` | Piper `joe` dataset | CC0 |

Both are `medium` quality Piper voices. They are genuinely different speakers, so
the two robots are audibly distinct — this is asserted by
`tests/real/test_piper_optional.py::test_the_two_voices_sound_different`.

Voices whose datasets restrict commercial use (`ryan`, `hfc_female`,
`hfc_male` — CC BY-NC-SA; `lessac` — Blizzard 2013 licence) were deliberately
avoided. See [THIRD_PARTY_AND_LICENSES.md](THIRD_PARTY_AND_LICENSES.md).

## Install

Models are **not** committed. Download both once (~122 MB total):

```powershell
cd D:\ClaudeCodeTest
.\.venv\Scripts\Activate.ps1
pip install -e "backend[tts]"
python -m piper.download_voices en_US-joe-medium en_US-kristin-medium --download-dir backend\storage\models
```

Result:

```
backend\storage\models\
  en_US-joe-medium.onnx         (~61 MB)
  en_US-joe-medium.onnx.json
  en_US-kristin-medium.onnx     (~61 MB)
  en_US-kristin-medium.onnx.json
```

Check what the server sees:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/tts/health
# provider=piper available=True voices_found=2 missing_models={}
```

If a model is missing, `/api/tts/health` lists it and the API returns
`TTS_UNAVAILABLE` with the exact download command. The text of every verse is
preserved — only the audio request fails, and pressing **Play** again retries.

## Prove it produces real audio

```powershell
pip install -e "backend[tts]"
python -m app.scripts.tts_smoke --voices-dir backend\storage\models --out backend\storage\audio\smoke
```

The script synthesizes one line per voice and fails (exit 1) unless the file is
over 10 KB, is a valid RIFF/WAVE, is 16-bit mono at 22 050 Hz, and is at least
0.8 s long. It prints byte counts, duration, synthesis time, peak RSS, and an
`ffprobe` summary when `ffprobe` is on `PATH`.

Real voice models behind the optional tests:

```powershell
pytest backend/tests/real -m piper
```

## How it works in the app

1. `POST /api/verses/{verse_id}/audio` looks up the verse and its character's
   voice. The voice must be in the code-level allowlist, or the request is
   rejected with `INVALID_VOICE`.
2. The cache key is `sha256(v1 | provider | voice_id | settings | normalized text)`.
   A ready asset with the same key is reused; an identical text already
   synthesized for another verse reuses the same file.
3. Otherwise Piper synthesizes into memory **while no database transaction is
   open**, and the bytes are validated as WAV before anything is stored.
4. The file is written atomically (`.tmp` + `os.replace`) to
   `AUDIO_STORAGE_DIR/YYYY/MM/<uuid4>.wav` and the row is saved.
5. The client receives `/api/audio/{audio_id}` — never a filesystem path.
   Serving resolves the stored relative key under the audio root and rejects
   traversal, returning `AUDIO_FILE_MISSING` if the file vanished.
6. A synthesis failure stores `status=failed` and leaves the verse and the
   battle's turn pointer untouched. `POST` again to retry.

Playback in the browser uses one hidden `<audio>` element. The "Speaking"
highlight is driven by the element's real `playing`/`pause`/`ended`/`error`
events, so it can never show a robot speaking when no sound is being produced.

## Tests

```powershell
# offline, no models needed (uses the fake tone provider)
pytest backend/tests -q

# real Piper, skipped automatically when models are absent
pytest backend/tests/real -m piper
```

## Caveats

- Piper is **GPL-3.0-or-later**. It is an optional extra, never vendored or
  bundled; the audio files it produces are not a derivative work of the engine.
  See [THIRD_PARTY_AND_LICENSES.md](THIRD_PARTY_AND_LICENSES.md).
- English (`en_US`) voices only in this MVP. Adding another language means
  adding a `Voice` entry and downloading that model.
- Synthesis is CPU-only and serialized per voice. Two verses from the *same*
  character cannot synthesize simultaneously; they wait on that voice's lock.
- Longer verses take longer. `TTS_MAX_TEXT_CHARS` (default 800) caps the input
  and `TTS_TIMEOUT_SECONDS` (default 60) bounds waiting, including first-load.
- `TTS_PROVIDER=fake` exists for offline tests only. It emits a valid tone, never
  speech, and the UI shows a "Test tone" chip whenever it is active.
