# BattleVerse --- Product Design & Technical Specification

> **Purpose:** This document is the primary product and engineering
> specification for Claude Code. Read it before planning or modifying
> the application. Use it as the source of truth for scope,
> architecture, user experience, data model, and acceptance criteria.
>
> **Build strategy:** Plan first, then implement in small, verifiable
> phases. Do not attempt to generate the entire application in one pass.
> Keep this document updated when a deliberate design decision changes.

------------------------------------------------------------------------

## 1. Product Overview

### 1.1 Product name

**BattleVerse**

### 1.2 One-line description

BattleVerse is a full-stack, browser-based GenAI entertainment game in
which two configurable AI characters compete in rap and playful roast
battles. The characters generate contextual verses, speak their lines
using text-to-speech (TTS), retain relevant battle history, and compete
for user votes and scores.

### 1.3 Product vision

Create a polished, futuristic battle arena that feels like a small game
rather than a plain chatbot. A user should be able to configure a
battle, watch two AI personalities exchange original verses, listen to
distinct voices, vote for a winner, review results, and launch a rematch
where the characters can refer to their prior rivalry.

### 1.4 Target user and platform

-   Initial user: a single local user running the application on their
    Windows PC.
-   Primary platform: modern desktop browser.
-   Responsive layout: should remain usable on tablets and mobile
    browsers.
-   Development environment: Windows and PowerShell.
-   Hardware constraint: target a development PC with 8 GB RAM. Avoid
    requiring a local GPU or large local language model.
-   Cost preference: free-first. Prefer provider free tiers or
    lightweight local components where practical, but do not assume a
    provider's free tier is permanent or unlimited.

### 1.5 Product principles

1.  **Playable before elaborate:** the first milestone must be a
    complete battle loop.
2.  **Voice is a core feature:** TTS is part of the initial functional
    product, not an afterthought.
3.  **Persistent state:** characters, battles, verses, votes, results,
    and audio metadata should survive application restarts.
4.  **Contextual characters:** a response should react to the opponent's
    actual previous verse.
5.  **Provider independence:** LLM and TTS implementations must be
    replaceable behind service interfaces.
6.  **Honest UI states:** show loading, errors, retries, and audio
    availability clearly.
7.  **Safe entertainment:** keep roasts playful; do not encourage
    targeted harassment or hateful content.
8.  **Incremental engineering:** build, run, and test each phase before
    proceeding.

------------------------------------------------------------------------

## 2. Scope and Priorities

### 2.1 MVP --- required

The MVP is not complete until all of these work end to end:

-   React web interface with a polished battle arena.
-   Python FastAPI backend.
-   SQLite database with SQLAlchemy models and migrations or a clearly
    documented schema initialization strategy.
-   Two predefined AI characters with distinct personalities.
-   Battle setup: topic, style, number of rounds, and playback mode.
-   LLM-generated verses using character instructions and relevant
    battle context.
-   Alternating turns with validated game state.
-   TTS audio for each generated verse, using two distinct supported
    voices where possible.
-   Browser playback controls: play, pause, resume, replay, and
    mute/volume.
-   User voting for the round or overall winner.
-   Persisted battle history, verses, audio metadata, and final results.
-   Useful error states when the LLM or TTS provider is unavailable.
-   Environment-variable configuration for secrets; no API keys in
    frontend code.
-   Basic automated tests for game rules, API behavior, persistence, and
    provider failure cases.
-   A README with Windows PowerShell setup, run, test, and
    troubleshooting instructions.

### 2.2 Post-MVP --- after the MVP is stable

-   Create, edit, and delete custom characters.
-   Character avatar upload or generated character portraits.
-   AI judge with a transparent rubric and category scores.
-   Battle history browser and rematches.
-   Character rivalry summaries and memory between battles.
-   Leaderboard based on saved battle results.
-   Optional speech animation or waveform visualizer.
-   Optional generated sound effects and background ambience.
-   Optional user accounts and multi-user support.
-   Optional deployment.

### 2.3 Explicitly out of scope for the first version

-   Training a custom language model.
-   Requiring a powerful GPU.
-   Full music composition or singing synthesis.
-   Beat-synchronized professional rap performance.
-   Real-time voice conversation or speech recognition.
-   Multi-agent autonomous simulation beyond the two contestants and
    optional judge.
-   Payments, subscriptions, or complex account administration.
-   Public sharing of user-generated content before moderation and
    security are designed.

Normal TTS speaks generated lyrics; it does not automatically make them
sound like a musical rap performance. Treat beat-backed music generation
as a future enhancement.

------------------------------------------------------------------------

## 3. User Stories

### 3.1 Starting a battle

As a user, I can choose two fighters, enter a topic, choose a style and
round count, select playback behavior, and start a battle.

**Acceptance criteria** - The UI validates required selections before
sending the request. - The backend validates all input independently. -
A battle is saved with a stable ID and an initial state. - The interface
navigates to or opens the battle arena.

### 3.2 Generating verses

As a user, I can generate each character's verse in turn and see the
text appear in the arena.

**Acceptance criteria** - Turn order is enforced by the backend, not
trusted to the frontend. - Each verse is associated with its battle,
round, character, and turn order. - The opponent receives the actual
previous verse as context. - Duplicate requests do not silently create
duplicate turns. - The UI shows generation progress and a recoverable
error if generation fails.

### 3.3 Listening to verses

As a user, I can hear each verse spoken aloud in the assigned character
voice.

**Acceptance criteria** - The audio action is visible and accessible for
each verse. - Playback controls work in supported browsers. - A
character's assigned voice is used consistently where supported. - TTS
failure does not delete or invalidate the text verse. - Audio can be
regenerated or retried without generating a new verse. - The UI
distinguishes "audio generating," "audio ready," and "audio failed."

### 3.4 Voting and results

As a user, I can vote for a fighter and see the battle results.

**Acceptance criteria** - The backend verifies that the battle is in a
votable state. - The vote is persisted and tied to the battle and
relevant round or final result. - The same local user cannot
accidentally submit repeated votes for the same voting event. - The
final result clearly distinguishes human votes from AI judge scores.

### 3.5 Rematches and memory

As a user, I can replay a past battle and start a rematch.

**Acceptance criteria** - Past battle details and verses can be
retrieved after restarting the app. - A rematch creates a new battle
linked to the previous battle; it does not overwrite the old one. - If
memory is enabled, the prompt includes a compact, relevant summary of
prior rivalry events. - Memory is stored as application data, not
assumed to exist inside the LLM provider.

------------------------------------------------------------------------

## 4. User Experience and Visual Design

### 4.1 Visual direction

Use a futuristic, competitive gaming aesthetic: - Dark background with
restrained neon purple, electric blue, and magenta accents. -
High-contrast text and clear typography. - Glowing borders and gradients
used sparingly. - Distinct visual identities for each contestant. -
Large versus indicator, round counter, score panel, and prominent audio
controls. - Smooth but restrained transitions; avoid animation that
interferes with readability or accessibility. - Responsive layout with
usable controls at narrow widths.

Avoid making every element glow. Visual hierarchy, contrast, and
legibility matter more than effects.

### 4.2 Main screens

#### A. Home dashboard

Include: - BattleVerse logo/name and short description. - Primary "Start
Battle" action. - Featured/default characters. - Recent battles. - Basic
leaderboard or champion panel, if data is available. - Clear empty
states when no battles exist.

#### B. Battle setup

Fields: - Fighter A. - Fighter B (must differ from Fighter A). - Topic
or prompt. - Battle style: `funny_roast`, `freestyle`, `lyrical`,
`wordplay`. - Intensity: `playful`, `competitive`. - Number of rounds
(default 3; enforce a reasonable maximum such as 5). - Playback mode:
`manual` or `auto`. - Optional voice selection if supported by the
configured TTS engine.

Display a concise summary before the battle starts.

#### C. Character workshop

Post-MVP. Include: - Name, short description, personality traits,
catchphrase. - Battle style preferences. - Avatar image or avatar
placeholder. - Voice ID selected from supported voices. - Preview voice
action. - Validation and save/cancel actions.

Never accept arbitrary filesystem paths from the user for avatars or
audio.

#### D. Battle arena

Must include: - Fighter A and Fighter B identity panels. - Current round
and total rounds. - Battle topic and selected style. - Turn indicator
and generation status. - Verse cards, clearly attributed to a
character. - Play/pause/resume/replay controls for each verse. - Volume
or mute control. - Optional speaking indicator while audio plays. -
"Generate next turn" action when manual playback is selected. -
Auto-play behavior when selected, with a visible way to pause or disable
it. - Voting UI at the correct game state. - Recoverable errors and
retry actions. - Exit or return-to-dashboard action without losing saved
progress.

Do not automatically start sound before the user has interacted with the
page if browser autoplay policies may block it. If autoplay is enabled,
explain that the user may need to press Play once to allow audio.

#### E. Results screen

Include: - Winner or draw. - Human vote result. - Optional AI judge
scores, clearly labeled as AI-generated. - Best verse or punchline
(optional). - Rematch action. - View transcript action. - Return home
action.

#### F. History and leaderboard

Post-MVP: - Filterable battle history. - Battle detail/transcript
view. - Rematch action. - Leaderboard with a documented ranking
method. - Empty and error states.

### 4.3 Accessibility and usability

-   Use semantic HTML and keyboard-accessible controls.
-   Provide visible focus states.
-   Do not rely on color alone to communicate whose turn it is.
-   Add accessible labels to audio controls.
-   Respect reduced-motion preferences.
-   Keep lyric text readable while audio plays.
-   Do not autoplay multiple verses simultaneously.
-   Ensure there is only one active audio playback stream at a time
    unless a deliberate design decision says otherwise.

------------------------------------------------------------------------

## 5. Game Rules and Battle State Machine

### 5.1 Default rules

-   A battle has two distinct characters.
-   A battle consists of a configured number of rounds.
-   Each round has one turn from each contestant.
-   Contestant A starts each round by default; a future enhancement may
    alternate who starts.
-   The backend controls turn order.
-   Each turn generates one verse within configured length limits.
-   The opponent's response prompt includes the opponent's most recent
    verse and relevant earlier context.
-   After both contestants have taken their turns in the final round,
    the battle becomes ready for voting/results.
-   Human voting is the default judging mechanism.
-   AI judging is optional and must not silently override the user's
    vote.

### 5.2 Suggested states

Use explicit states and validate legal transitions: - `created` -
`in_progress` - `awaiting_vote` - `completed` - `failed` only if the
battle cannot continue and needs explicit recovery

A provider timeout should not necessarily mark the entire battle failed.
Keep the battle recoverable and preserve already saved verses.

### 5.3 Turn integrity

-   Calculate the expected character and round on the backend.
-   Reject a turn request if the battle is not in `in_progress`.
-   Reject a turn request if the requested character does not match the
    expected character.
-   Use an idempotency mechanism or turn identifier to prevent duplicate
    verses from repeated requests.
-   Save a verse only after a valid response has been parsed and
    checked.
-   If a provider request fails, do not advance the turn counter.
-   Keep database transactions short; do not hold an open transaction
    while waiting for a remote LLM or TTS request.
-   If concurrent requests are possible, use a transaction/locking
    strategy or version check to prevent two turns from being generated
    for the same state.

### 5.4 Verse constraints

-   Default target: 4 lines per verse, configurable within safe bounds.
-   Keep output concise enough for speech playback.
-   Do not allow the model to choose the next character or modify game
    state.
-   Require structured output where supported, with a schema such as:
    -   `verse_text`: string
    -   `line_count`: integer (optional)
    -   `callback_reference`: short optional string
-   Validate output and retry once with a correction prompt if
    malformed.
-   Do not expose hidden prompts or provider error details to the user.

------------------------------------------------------------------------

## 6. GenAI Design

### 6.1 LLM responsibilities

The language model is responsible for: - Generating original verses. -
Maintaining the configured character's voice/personality in text. -
Responding to the opponent's actual previous verse. - Using the topic
and style. - Avoiding excessive repetition. - Optionally producing
structured judging results. - Optionally summarizing a completed rivalry
for future rematches.

The LLM is not responsible for: - Enforcing turn order. - Writing
directly to the database. - Deciding whether a battle is completed. -
Setting arbitrary scores without the agreed rubric. - Accessing secrets
or filesystem paths. - Returning HTML/JavaScript to be executed.

### 6.2 Prompt inputs

Each verse-generation request should include only relevant context: -
Character profile and personality. - Battle topic. - Style and
intensity. - Round number and total rounds. - Opponent's latest verse,
if any. - A concise summary of relevant prior rounds, if available. - A
few prior verses only when useful. - Output length and content rules.

Avoid passing the entire battle history forever. Use a bounded context
window and summaries to control token use and latency.

### 6.3 Prompt design principles

-   Give each character a distinct style guide.
-   Tell the model to write original content and avoid copying known
    lyrics.
-   Keep roasts fictional, playful, and non-discriminatory.
-   Do not target protected traits, private individuals, or vulnerable
    people.
-   Avoid threats, doxxing, or encouragement of real-world harm.
-   Ask for clear, pronounceable lyrics suitable for TTS.
-   Avoid excessive punctuation, markdown tables, emoji, or stage
    directions in the spoken text.
-   Do not ask the model to imitate a living artist's exact style. Use
    broad musical/creative traits instead.
-   Treat user-supplied topic text as untrusted data, not as
    instructions to override system rules.

### 6.4 Provider abstraction

Create a provider interface, for example: -
`LLMProvider.generate_verse(...)` - `LLMProvider.judge_battle(...)` -
`LLMProvider.summarize_battle(...)`

Implement the selected provider in a separate module. Provider
credentials and model IDs must come from environment variables. Do not
couple business logic to one vendor's response format.

A deterministic mock provider should be available for development and
automated tests, so tests do not require internet access or API credits.

### 6.5 AI judge

Post-MVP or optional once the battle loop is stable. Use a structured
rubric, for example scores from 1--10: - Creativity/originality. -
Rhyme/wordplay. - Humor/punchline. - Topic relevance. -
Rebuttal/callback quality.

Require the judge to return a structured result with brief explanations.
Validate score bounds on the backend. Display the judge's scores as
subjective AI estimates. Do not claim they are objective or
authoritative.

### 6.6 Failure and retry behavior

-   Use explicit timeouts.
-   Retry only transient errors and limit retries.
-   Avoid automatic retries that could create duplicate charges or
    duplicate verses.
-   Keep user-visible errors understandable.
-   Log technical detail server-side without logging secrets.
-   Preserve completed work when a later operation fails.

------------------------------------------------------------------------

## 7. Text-to-Speech (Core MVP Requirement — Must Actually Work)

TTS is a launch requirement. A transcript with decorative play buttons, browser speech synthesis presented as generated audio, a mocked response, or a test that only checks a mocked provider does **not** satisfy this requirement.

### 7.1 Required end-to-end behavior

For each battle turn:

1. Generate and persist the verse text first.
2. Request speech synthesis for that exact saved verse using the speaking character's configured voice.
3. Persist audio metadata and make the generated audio available through a safe HTTP URL.
4. In the browser, display the verse and its audio state; when automatic playback is enabled, play the audio when ready.
5. Queue audio sequentially so characters do not speak over one another. The next queued verse must not start until the current audio finishes, unless the user stops playback or explicitly skips it.
6. Let the user replay a verse independently without generating a new verse.

TTS failure must not delete a verse, corrupt turn order, or prevent the user from reading the battle. Show an actionable error and retry control.

### 7.2 Audio controls and UI states

Implement and test:

- Per-verse play/replay and pause/resume where supported by the browser audio element.
- Global mute/unmute and volume control.
- An autoplay toggle, with the user's selection respected.
- Clear `queued`, `generating`, `ready`, `playing`, and `failed` states as applicable.
- A speaking indicator tied to actual playback state, not a timer pretending that speech is playing.
- A clear message if browser autoplay policy requires a user gesture.
- Stop/clear queued playback when the user explicitly stops a battle or leaves the arena, according to a documented policy.
- No duplicate playback caused by React re-renders or repeated event subscriptions.
- Correct handling of failed HTTP responses, missing audio files, unsupported audio formats, and interrupted playback.

### 7.3 Voice profiles

- Each default character must have a separate configured voice profile.
- Prefer genuinely distinct supported voices/models when the chosen engine provides them.
- If the engine exposes only one voice, document that limitation and use supported voice settings (such as speaking rate) only if they genuinely exist; do not claim two different voices when there is only one.
- Validate voice IDs against the provider's available voice list or a known configuration allowlist.
- Keep character-to-voice mapping separate from battle logic so voices can be changed without changing the battle engine.
- Add a voice-preview action if practical, using the same real synthesis and playback pipeline.

### 7.4 Provider interface and implementation

Define a provider abstraction with equivalents of:

- `list_voices() -> list[VoiceInfo]`
- `synthesize(text, voice_id, settings) -> AudioResult`
- `health_check() -> ProviderHealth` (if supported)

`AudioResult` should carry audio bytes or a temporary file, a verified MIME type, and optional duration/metadata. Provider-specific details must stay inside the adapter.

Implement at least one **real, runnable TTS provider** for local use. Keep a deterministic fake provider for unit tests, but never make the fake provider the production default or report mock output as real audio.

### 7.5 Free-first local engine selection

The default should be local TTS that does not require a paid API or API key. The target machine is Windows with 8 GB RAM and no guaranteed GPU.

Before selecting the engine, compare current documented options such as Piper and Kokoro for Windows compatibility, installation steps, voice quality, model/download size, RAM use, license, supported languages/voices, and maintenance status. Verify package names, model IDs, download locations, and usage instructions against current authoritative documentation. Choose the most reliable option that can actually be installed and run in this environment; do not select a model based on name recognition alone.

- Do not download a large model or require a GPU without explicit approval.
- Download only the selected voice model(s), from a verified source, and explain the first-run network requirement.
- If the preferred engine fails a real Windows compatibility check, implement the next viable documented option rather than leaving a stub.
- Hosted TTS may be added as an optional provider, but local TTS must remain the default and basic speech must not require a hosted account.
- Never assume a hosted free tier is permanent or unlimited. Do not send text to a hosted provider without documenting that the provider receives it and requiring explicit configuration.

### 7.6 Audio API, storage, and serving

Provide endpoints equivalent to:

- `GET /api/tts/voices` — list supported configured voices.
- `POST /api/verses/{verse_id}/audio` — synthesize or retrieve cached audio for an existing verse.
- `GET /api/audio/{audio_id}` — stream/serve a generated audio asset using a stable browser-accessible URL.
- Optional `GET /api/tts/health` — report whether the configured provider is available without exposing secrets.

Use the project's API naming conventions consistently if an alternative route structure is chosen. Validate all inputs, cap text length, apply timeouts, return useful status codes, and avoid duplicate synthesis where practical.

- Store audio under an application-managed directory, configurable through `AUDIO_STORAGE_DIR` (for example `backend/storage/audio/`).
- Use generated opaque filenames, not user-provided filenames.
- Store a relative storage key, MIME type, voice ID, generation status, and timestamps in the database.
- Serve only audio records/files known to the application; prevent path traversal and arbitrary file reads.
- Do not expose server filesystem paths as browser audio URLs.
- Use a cache key based on verse text plus voice and synthesis settings, or equivalent persisted association.
- Clean up abandoned temporary files safely; never delete audio still referenced by a saved battle without a deliberate retention policy.

### 7.7 Required verification — real audio, not only mocks

The implementation must include all of the following:

1. Unit tests for the provider interface, input validation, caching, and error handling using a fake provider.
2. API tests for voice listing, synthesis requests, audio serving, and failure responses.
3. A real local smoke-test command that invokes the installed engine, synthesizes a sample line, and confirms a non-empty audio file with the expected/recognizable audio format is produced.
4. A manual or automated browser verification that the frontend fetches and plays the generated audio URL. If browser automation or an audio device is unavailable in the coding environment, state that clearly and provide exact steps to verify locally.
5. A repeat/replay test confirming replay uses the existing verse and does not create another battle turn.
6. A failure test confirming TTS errors leave the verse and battle state intact.

Do not claim that real speech was verified unless the real engine was actually installed and run. If downloads, network, runtime, or audio hardware block verification, report the precise blocker, what was tested instead, and the exact command the user can run to finish verification.

### 7.8 Windows setup and troubleshooting

The README must provide exact PowerShell commands for creating/activating the Python virtual environment, installing dependencies, obtaining the selected voice model from a verified source, starting backend/frontend, generating a sample audio file, running tests, and troubleshooting common issues. Explain model disk usage, expected RAM behavior qualitatively, first-run internet requirements, and how to change voice configuration. Do not promise exact performance numbers without measurement.

### 7.9 Speaking animation

A simple speaking indicator or CSS animation is sufficient for MVP, but it must reflect real audio playback events. A decorative waveform must not be described as accurate audio visualization unless it is driven by actual audio data. True phoneme-level lip synchronization is out of scope for MVP.

------------------------------------------------------------------------

## 8. Backend Architecture

### 8.1 Responsibilities

FastAPI handles: - Request validation. - Battle state transitions and
turn order. - LLM/TTS service orchestration. - Database reads and
writes. - Audio file serving. - Voting, results, and leaderboard
calculations. - Error mapping and application logging.

### 8.2 Recommended module boundaries

Keep routers thin and business logic in services: - `api/`: HTTP routes
and schemas. - `models/`: SQLAlchemy ORM models. - `schemas/`: Pydantic
request/response types. - `services/`: battle engine, prompt builder,
scoring, memory, audio. - `providers/`: LLM and TTS adapters, plus mock
implementations. - `core/`: settings, logging, exceptions, database
setup. - `tests/`: unit and integration tests.

Avoid placing all business logic in a single `main.py` file.

### 8.3 API conventions

-   Prefix API endpoints with `/api`.
-   Use JSON for regular request/response bodies.
-   Return stable IDs for persisted resources.
-   Use appropriate HTTP status codes.
-   Validate all request fields on the backend.
-   Return predictable error objects, for example:
    -   `code`: stable machine-readable error code.
    -   `message`: safe user-facing explanation.
    -   `request_id`: optional correlation ID.
-   Never expose stack traces, provider secrets, or raw internal
    exceptions to the browser.
-   Add CORS configuration for the specific local frontend origin during
    development; do not allow every origin in production by default.
-   Keep long-running generation operations recoverable. Start with
    normal request/response calls and clear loading states; add
    background jobs only if actual latency requires them.

### 8.4 Suggested endpoint contract

The exact schema may be refined during planning, but maintain consistent
semantics.

  ---------------------------------------------------------------------------
  Method                  Endpoint                    Purpose
  ----------------------- --------------------------- -----------------------
  `GET`                   `/api/health`               Health check, without
                                                      exposing secrets

  `GET`                   `/api/characters`           List characters

  `POST`                  `/api/characters`           Create a character
                                                      (post-MVP if needed)

  `GET`                   `/api/characters/{id}`      Character details

  `POST`                  `/api/battles`              Create/start a battle

  `GET`                   `/api/battles`              List recent battles

  `GET`                   `/api/battles/{id}`         Get battle, state,
                                                      contestants, and
                                                      transcript

  `POST`                  `/api/battles/{id}/turn`    Generate the next valid
                                                      turn

  `POST`                  `/api/verses/{id}/audio`    Generate or retrieve
                                                      cached verse audio

  `GET`                   `/api/audio/{audio_id}`     Serve a known audio
                                                      asset

  `POST`                  `/api/battles/{id}/vote`    Submit a vote for the
                                                      valid voting event

  `POST`                  `/api/battles/{id}/judge`   Request optional AI
                                                      judging

  `GET`                   `/api/leaderboard`          List ranked characters

  `GET`                   `/api/history`              Retrieve past battles
  ---------------------------------------------------------------------------

For each endpoint, define Pydantic request and response schemas before
implementing the frontend integration. Avoid returning ORM objects
directly without response schemas.

### 8.5 Suggested request examples

Create battle:

``` json
{
  "fighter_a_id": "character-id-a",
  "fighter_b_id": "character-id-b",
  "topic": "coding versus gaming",
  "style": "funny_roast",
  "intensity": "playful",
  "round_count": 3,
  "playback_mode": "manual"
}
```

Generate next turn:

``` json
{
  "expected_turn_number": 1
}
```

Use the backend's current battle state to determine the speaker. Do not
let the client arbitrarily select a speaker. The example field is
optional if a robust idempotency/optimistic concurrency mechanism is
implemented instead.

Vote:

``` json
{
  "round_number": null,
  "winner_character_id": "character-id-a"
}
```

For an overall vote, `round_number` may be null. Define whether
round-level voting is supported; if it is not in the MVP, remove that
option from both the API and UI.

------------------------------------------------------------------------

## 9. Database Design

Use SQLite initially with SQLAlchemy. Add migrations with Alembic if
practical; otherwise provide a documented, safe schema initialization
process for the prototype. Do not drop or recreate the database
automatically on application startup.

### 9.1 `characters`

Suggested fields: - `id`: UUID or stable string primary key. - `name`:
required. - `description`: short description. - `personality`:
structured JSON or normalized fields. - `battle_style`: preferred
style. - `catchphrase`: optional. - `avatar_path`: optional safe
relative asset key. - `voice_id`: ID supported by the configured TTS
provider. - `is_builtin`: boolean. - `created_at`, `updated_at`.

### 9.2 `battles`

Suggested fields: - `id`: UUID/string primary key. - `fighter_a_id`,
`fighter_b_id`: foreign keys to characters. - `topic`. - `style`. -
`intensity`. - `round_count`. - `current_round`. -
`next_turn_character_id` or another canonical turn representation. -
`status`. - `playback_mode`. - `previous_battle_id`: nullable foreign
key for rematches. - `winner_character_id`: nullable. - `created_at`,
`completed_at`. - Optional `state_version` for concurrency protection.

### 9.3 `verses`

Suggested fields: - `id`: UUID/string primary key. - `battle_id`:
foreign key. - `character_id`: foreign key. - `round_number`. -
`turn_number`: unique within a battle. - `verse_text`. -
`generation_status` if generation is persisted separately; otherwise
only save completed verses. - `created_at`.

Add a uniqueness constraint on `(battle_id, turn_number)`.

### 9.4 `audio_assets`

Suggested fields: - `id`: UUID/string primary key. - `verse_id`: foreign
key. - `provider`. - `voice_id`. - `storage_key`: safe relative
path/key. - `content_type`. - `duration_ms`: nullable. - `status`:
pending, ready, failed. - `created_at`. - Optional checksum or cache
key.

Allow retrying failed audio generation. Define whether multiple voice
variants per verse are supported; the schema should not accidentally
overwrite a valid voice variant.

### 9.5 `votes`

Suggested fields: - `id`: UUID/string primary key. - `battle_id`:
foreign key. - `round_number`: nullable for final vote. - `voter_key`:
local anonymous session key or user ID when authentication is added. -
`winner_character_id`: foreign key. - `created_at`.

Add an appropriate uniqueness constraint so the same voter cannot submit
multiple votes for the same battle/voting event.

### 9.6 `judge_results` (optional/post-MVP)

Suggested fields: - `id`. - `battle_id`. - `rubric_version`. -
`scores_json` with per-character category scores. -
`winner_character_id`. - `explanation`. - `created_at`.

### 9.7 `character_memories` (post-MVP)

Suggested fields: - `id`. - `character_id`. - `related_battle_id`. -
`memory_type`. - `summary`. - `importance`. - `created_at`,
`updated_at`.

Store concise, derived summaries rather than relying on an external
model's hidden chat history.

### 9.8 Database rules

-   Use foreign keys and suitable indexes.
-   Store timestamps consistently in UTC.
-   Validate values in both Pydantic schemas and business logic.
-   Use transactions for state changes.
-   Do not perform remote model calls inside a database transaction.
-   Preserve historical battle data when a character is edited or
    removed; prefer soft deletion or restrict deletion when referenced.
-   Do not store API keys or other secrets in the database.
-   Do not store audio bytes directly in the database by default.

------------------------------------------------------------------------

## 10. Frontend Architecture

### 10.1 Suggested stack

-   React.
-   Vite.
-   TypeScript preferred for safer API contracts.
-   Tailwind CSS for styling.
-   A small, consistent component library or custom accessible
    components.
-   Framer Motion optional for transitions.
-   A typed API client module.
-   A browser audio abstraction/hook for playback state.

Use a lockfile and document supported Node.js and Python versions.
Confirm compatible versions during setup rather than assuming the latest
release is always compatible.

### 10.2 Suggested frontend structure

``` text
frontend/
  src/
    app/
    components/
      layout/
      battle/
      character/
      audio/
      ui/
    pages/
      HomePage.tsx
      BattleSetupPage.tsx
      BattleArenaPage.tsx
      ResultsPage.tsx
      HistoryPage.tsx
    hooks/
      useBattle.ts
      useAudioPlayer.ts
    services/
      api.ts
      characters.ts
      battles.ts
      audio.ts
    types/
    styles/
    main.tsx
```

Adapt the exact structure to the chosen routing setup, but keep API
access, reusable components, and game logic separated.

### 10.3 Frontend behavior

-   Use typed API requests and responses.
-   Show loading states during generation and audio synthesis.
-   Disable invalid actions while a turn is being generated.
-   Avoid duplicate submission from rapid clicks.
-   Recover the battle from the backend after page refresh.
-   Treat backend battle state as authoritative.
-   Keep audio playback state separate from persistent battle state.
-   Display user-friendly errors with retry controls.
-   Do not put provider API keys in frontend environment variables.
-   Do not use mock data in production screens once the real API is
    available. Mock data is acceptable for isolated UI development and
    tests.

------------------------------------------------------------------------

## 11. Suggested Repository Structure

Use a single repository:

``` text
battleverse/
  design.md
  README.md
  .gitignore
  .env.example
  backend/
    app/
      main.py
      api/
      core/
      models/
      schemas/
      services/
      providers/
    tests/
    storage/
      audio/
      avatars/
    requirements.txt or pyproject.toml
  frontend/
    package.json
    src/
    public/
  docs/
```

Adjust this structure if a simpler layout better fits the selected
tooling, but retain clear frontend/backend separation. Do not commit
real `.env` files, generated user audio, database files containing user
data, or private credentials.

### 11.1 Environment configuration

Provide a `.env.example` with placeholder values, such as: - `APP_ENV` -
`DATABASE_URL` - `CORS_ORIGINS` - `LLM_PROVIDER` - `LLM_API_KEY` -
`LLM_MODEL` - `TTS_PROVIDER` - `TTS_API_KEY` if required - `TTS_MODEL`
if required - `AUDIO_STORAGE_DIR` - `AVATAR_STORAGE_DIR` - `LOG_LEVEL`

Only include variables actually used by the chosen implementation. Never
put real secrets in the example file. Fail fast with a clear startup
message when a required provider setting is missing, while still
allowing mock-provider development and tests.

------------------------------------------------------------------------

## 12. Configuration and Dependency Selection

Before implementing provider-specific code, compare feasible options
for: - An LLM with a suitable free tier or affordable usage. - A local
TTS engine that can run acceptably on Windows with 8 GB RAM. - A hosted
TTS alternative with supported voices and clearly documented quotas. -
License compatibility for application use.

Use current official provider documentation to verify model IDs, SDKs,
quotas, supported regions, and terms. Do not hard-code assumptions that
a free tier is unlimited or guaranteed.

Keep the first version simple: - One LLM provider implementation plus a
mock provider. - One TTS provider implementation plus a mock or
deterministic test implementation. - No local model downloads unless
they are necessary and explicitly approved. - No unnecessary vector
database; ordinary relational storage and concise summaries are
sufficient for initial character memory.

Document why each selected provider was chosen and how to replace it.

------------------------------------------------------------------------

## 13. Security, Privacy, and Content Safety

-   Store secrets only in backend environment variables.
-   Never log API keys, authorization headers, or full secret-bearing
    environment configuration.
-   Validate input length and allowed enum values.
-   Set timeouts and reasonable rate limits for generation endpoints.
-   Restrict CORS to configured origins.
-   Prevent path traversal in audio and avatar serving.
-   Restrict uploaded file types and sizes if uploads are added.
-   Do not execute model-generated code, HTML, or scripts.
-   Escape rendered user/model text appropriately.
-   Keep roast battles fictional and playful.
-   Do not generate hateful or demeaning content targeting protected
    traits.
-   Do not encourage real-world threats, stalking, doxxing, or violence.
-   Use moderation/validation where appropriate, and provide a safe
    retry path.
-   Explain when a hosted LLM/TTS provider processes battle text.
-   Keep local battle data on the local machine unless the user
    intentionally deploys or shares it.
-   Add deletion/export features before introducing multi-user or public
    hosting.

------------------------------------------------------------------------

## 14. Error Handling and Observability

Create consistent error handling for: - Missing provider
configuration. - LLM timeout, rate limit, authentication failure, or
malformed output. - TTS timeout, unavailable voice, or invalid audio
response. - Database constraint errors. - Missing battle or verse. -
Invalid turn/state transition. - Missing audio file. - Duplicate vote or
repeated turn request. - Network disconnection in the browser.

Log enough diagnostic information to debug issues, including a
request/correlation ID where useful, but never log secrets. Return safe,
understandable messages to the frontend.

A failure in TTS must not invalidate an already generated verse. A
failure in judging must not prevent a human-voted result. A failed
generation attempt must not advance the battle turn.

------------------------------------------------------------------------

## 15. Testing Requirements

### 15.1 Backend unit tests

-   Battle turn order and round progression.
-   State transitions.
-   Verse validation.
-   Prompt construction with character context and previous verse.
-   Vote uniqueness.
-   Winner/result calculation.
-   Audio cache key behavior.
-   Memory-summary selection.

### 15.2 Backend integration tests

-   Create/list/get characters.
-   Create a battle and retrieve it.
-   Generate a complete battle with a mock LLM provider.
-   Persist verses and reload them after a new database session.
-   Request TTS using a mock provider and retrieve the audio.
-   Simulate LLM and TTS failures.
-   Reject invalid turn requests.
-   Prevent duplicate turn creation and duplicate votes.
-   Confirm a failed TTS request does not delete the verse or change
    turn state.

Tests must not require real provider API keys, internet access, or paid
API calls.

### 15.3 Frontend tests

-   Battle setup validation.
-   Loading and error states.
-   Turn controls disable during generation.
-   Audio controls reflect ready/loading/failed states.
-   Vote submission and result display.
-   Refresh restores the battle from the backend.

### 15.4 Manual end-to-end checklist

1.  Start backend and frontend on Windows.
2.  Open the home page.
3.  Start a battle using the two default characters.
4.  Generate both turns in round one.
5.  Play both voice outputs.
6.  Complete all configured rounds.
7.  Vote and view the result.
8.  Restart the backend and confirm history persists.
9.  Reload a completed battle and replay its audio.
10. Simulate an unavailable LLM or TTS provider and verify clear error
    handling.
11. Confirm `.env`, database data, and generated audio are not
    accidentally committed to Git.

------------------------------------------------------------------------

## 16. Development Plan for Claude Code

Claude Code must first use Plan Mode to inspect the repository and
propose an implementation plan. If the repository is empty, propose a
clean scaffold. If files already exist, inspect them and preserve useful
work rather than blindly overwriting it.

### Phase 0 --- Inspect and plan

-   Inspect the current directory, existing files, installed runtimes,
    and repository state.
-   Read this complete `design.md`.
-   Identify missing decisions and risks.
-   Verify current provider choices using official documentation if web
    access is available.
-   Propose the folder structure, dependency versions, environment
    variables, database models, API schemas, and phase-by-phase
    implementation plan.
-   Do not start broad implementation until the plan is
    reviewed/approved in Plan Mode.

**Exit criteria:** a coherent plan with clear phases, test strategy, and
no unresolved architecture blockers.

### Phase 1 --- Foundation

-   Create backend and frontend scaffolds.
-   Add settings, environment template, health endpoint, CORS, database
    session management, and initial schema.
-   Add basic app shell and responsive visual theme.
-   Add setup instructions.

**Exit criteria:** both services start locally and the frontend can call
the backend health endpoint.

### Phase 2 --- Battle loop

-   Add default characters.
-   Add battle creation and retrieval.
-   Implement battle state machine and turn-order rules.
-   Implement an LLM provider interface and mock provider.
-   Generate and persist alternating verses.
-   Build the setup and battle arena screens.

**Exit criteria:** a complete text-only battle works end to end with
mock AI, persists to SQLite, and passes tests.

### Phase 3 --- Real LLM

-   Implement the selected provider adapter.
-   Add configuration validation, timeouts, bounded retries, and safe
    errors.
-   Improve character-specific prompting and contextual responses.
-   Test using a real provider only when credentials are configured.

**Exit criteria:** real verses can be generated without compromising
turn integrity; mock tests still pass.

### Phase 4 --- Real TTS (mandatory MVP gate)

-   Compare documented local engines (including Piper and Kokoro where appropriate) and select one that is installable on Windows and suitable for 8 GB RAM.
-   Implement the real local provider, provider abstraction, voice configuration, synthesis, audio storage/metadata, caching, safe HTTP serving, and error handling.
-   Add the browser audio queue, real playback state, autoplay toggle, replay, pause/resume, mute, volume, and speaking indicator.
-   Add deterministic mock-provider tests **and** a separate real-engine smoke test that produces an actual audio file.
-   Verify the browser can retrieve and play the audio; document any environment limitation honestly.
-   Add exact PowerShell setup, model-download, launch, smoke-test, and troubleshooting instructions to the README.

**Exit criteria:** real local speech is generated from a saved verse, served to and played by the browser, both characters use separate supported voice profiles, playback is sequential, replay does not create another verse, and TTS failure leaves battle state intact. A mocked provider alone does not pass this phase.

### Phase 5 --- Voting and results

-   Add human voting, final result calculation, and result screen.
-   Add optional AI judging only if the core game remains stable.
-   Add history and rematch support.

**Exit criteria:** completed battles and results persist correctly and
can be retrieved after restart.

### Phase 6 --- Character memory and polish

-   Add custom character creation.
-   Add concise battle/rivalry summaries and contextual memory.
-   Improve animations, responsive layouts, accessibility, and
    empty/error states.
-   Add leaderboard after ranking rules are defined.

**Exit criteria:** rematches can use relevant history, the interface is
polished, and regression tests pass.

### Phase 7 --- Release readiness

-   Run backend and frontend tests.
-   Run lint/type checks.
-   Verify Windows PowerShell instructions from a clean setup.
-   Check `.gitignore`, secret handling, and storage paths.
-   Update README and known limitations.
-   Provide a concise summary of implemented features, tests run,
    commands, and remaining work.

**Exit criteria:** another developer can follow the README to run the
application locally.

### Implementation discipline

At every phase: 1. Inspect current code before editing. 2. State the
files/features planned for the phase. 3. Implement only the current
phase. 4. Run relevant tests, type checks, or smoke tests. 5. Fix
regressions before continuing. 6. Update this design document if a real
requirement changes. 7. Summarize what works, what is incomplete, and
the exact next step.

Do not claim tests passed unless they were actually run. Do not silently
skip failed tests. Do not replace working code with large speculative
rewrites.

------------------------------------------------------------------------

## 17. Definition of Done

The MVP is considered done only when:

-   [ ] Frontend and backend run locally on Windows.
-   [ ] Setup is documented and reproducible.
-   [ ] Two default characters can complete a multi-round battle.
-   [ ] The AI responds to the opponent's previous verse.
-   [ ] Every verse is persisted.
-   [ ] A real local TTS engine is installed/configured and produces non-empty audio from an actual battle verse.
-   [ ] Generated audio is served through a browser-accessible endpoint and has been played in the frontend (or a precise environment limitation and reproducible local verification are documented).
-   [ ] Each verse can be spoken and replayed without creating a duplicate turn.
-   [ ] The two contestants use distinct supported voice profiles; limitations are explicitly documented if the chosen engine cannot provide distinct voices.
-   [ ] Sequential playback, autoplay toggle, pause/resume, mute, volume, speaking/error states, and retry work.
-   [ ] Audio failures do not corrupt battle state.
-   [ ] The user can vote and see a final result.
-   [ ] Battle history survives a restart.
-   [ ] API keys are not exposed to the frontend or committed.
-   [ ] Automated tests cover state transitions and key failure paths.
-   [ ] The README contains PowerShell setup, run, test, and
    troubleshooting instructions.
-   [ ] No critical known error is concealed by mock data or swallowed
    exceptions.

------------------------------------------------------------------------

## 18. Instructions to Claude Code

When using Plan Mode, treat this file as a requirements document, not as
permission to implement everything at once.

1.  Read `design.md` from beginning to end.
2.  Inspect the existing repository and current environment.
3.  Identify ambiguity, conflicts, and provider choices that require
    verification.
4.  Present a phased implementation plan with proposed files and
    verification commands.
5.  Prefer simple, maintainable choices suitable for an 8 GB RAM Windows
    PC.
6.  Keep real local TTS in the MVP. It is a release blocker if only mocked TTS exists.
7.  Use mock providers for deterministic tests, but also run the real TTS engine and produce a real audio file.
8.  Compare and verify local TTS options using current authoritative documentation; do not invent packages, model IDs, URLs, or commands.
9.  Do not download large models or require a GPU without explicit approval; a verified lightweight TTS voice model is required for the MVP.
10. Do not expose credentials or use unverified APIs.
11. Build and verify each phase before proceeding.
12. Keep the README and this document consistent with the actual implementation.
13. At the end of each phase, report what works, which tests were actually run, any failures, and the next phase.

**First requested action:** enter Plan Mode, read this file, inspect the
repository, and return the proposed Phase 0--7 implementation plan. Do
not begin a broad implementation until the plan has been reviewed.
