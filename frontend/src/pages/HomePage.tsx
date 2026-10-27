import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { paletteFor, RobotAvatar, variantForName } from "../components/character/RobotAvatar";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useHealth } from "../hooks/useHealth";
import { fetchCharacters, fetchHistory } from "../services/battles";
import type { BattleSummary, Character } from "../types/api";

export function HomePage() {
  useDocumentTitle("");
  const navigate = useNavigate();
  const { health, loading: healthLoading } = useHealth();
  const [characters, setCharacters] = useState<Character[]>([]);
  const [recent, setRecent] = useState<BattleSummary[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    fetchCharacters(controller.signal)
      .then(setCharacters)
      .catch(() => setCharacters([]));
    fetchHistory(controller.signal)
      .then((data) => setRecent(data.slice(0, 4)))
      .catch(() => setRecent([]));
    return () => controller.abort();
  }, []);

  return (
    <AppShell>
      <section className="mb-8 text-center">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          Two robots. One mic. Zero chill.
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-[var(--color-muted)]">
          Pick a topic, hit start, and let Nova Vex and Rook Blaze trade verses out loud.
          Then you decide who won.
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <Button variant="primary" size="lg" onClick={() => navigate("/battle/new")}>
            Start a battle
          </Button>
          <Button variant="secondary" size="lg" onClick={() => navigate("/history")}>
            Browse history
          </Button>
        </div>
      </section>

      {health && (!health.groq_key_present || !health.gemini_key_present) ? (
        <Banner tone="warn" className="mb-6">
          <strong>Model keys missing.</strong> Configure{" "}
          {!health.groq_key_present ? <code>GROQ_API_KEY</code> : null}
          {!health.groq_key_present && !health.gemini_key_present ? " and " : null}
          {!health.gemini_key_present ? <code>GEMINI_API_KEY</code> : null} in your local{" "}
          <code>.env</code> file and restart the backend. Each fighter uses its assigned provider.
        </Banner>
      ) : null}

      {health?.tts_provider === "fake" ? (
        <Banner tone="warn" className="mb-6">
          <strong>Synthetic test tone.</strong> <code>TTS_PROVIDER=fake</code> is active, so
          playback is a generated tone rather than speech.
        </Banner>
      ) : null}

      {health && !health.tts_ready && health.tts_provider === "piper" ? (
        <Banner tone="warn" className="mb-6">
          <strong>Voice models are missing.</strong> Download them once with:
          <code className="mt-1 block overflow-x-auto rounded bg-white/60 px-2 py-1 text-xs">
            python -m piper.download_voices en_US-joe-medium en_US-kristin-medium --download-dir backend\storage\models
          </code>
        </Banner>
      ) : null}

      <section aria-label="The robots" className="grid gap-4 sm:grid-cols-2">
        {characters.map((character) => {
          const palette = paletteFor(character.accent);
          return (
            <article
              key={character.id}
              className="bv-card bv-transition flex flex-col items-center gap-2 px-5 py-6 text-center hover:shadow-[var(--shadow-lift)]"
              style={{ borderTopWidth: 6, borderTopColor: palette.body }}
            >
              <RobotAvatar
                accent={character.accent}
                variant={variantForName(character.name)}
                size={110}
                label={character.name}
              />
              <h2 className="text-xl font-extrabold">{character.name}</h2>
              <p className="text-sm text-[var(--color-muted)]">{character.tagline}</p>
              <p className="text-sm">{character.description}</p>
              <p className="mt-1 rounded-full bg-[#f5f1ec] px-3 py-1 text-xs text-[var(--color-muted)]">
                Voice: {character.voice_id.replace("en_US-", "").replace("-medium", "")}
              </p>
            </article>
          );
        })}
      </section>

      <section className="mt-8" aria-label="Recent battles">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-bold">Recent battles</h2>
          {recent.length > 0 ? (
            <Link to="/history" className="text-sm font-semibold text-[var(--color-primary-ink)] no-underline hover:underline">
              See all →
            </Link>
          ) : null}
        </div>
        {recent.length === 0 ? (
          <EmptyState title="No battles yet" action={<Button onClick={() => navigate("/battle/new")}>Start one</Button>}>
            Your first battle will show up here.
          </EmptyState>
        ) : (
          <ul className="grid gap-2">
            {recent.map((battle) => (
              <li key={battle.id}>
                <Link
                  to={battle.status === "completed" ? `/battle/${battle.id}/result` : `/battle/${battle.id}`}
                  className="bv-card bv-transition flex flex-wrap items-center gap-3 px-4 py-3 text-[var(--color-ink)] no-underline hover:shadow-[var(--shadow-lift)]"
                >
                  <span className="text-sm font-bold">
                    {battle.fighter_a_name} vs {battle.fighter_b_name}
                  </span>
                  <span className="truncate text-xs text-[var(--color-muted)]">{battle.topic}</span>
                  <span className="ml-auto text-xs font-semibold text-[var(--color-muted)]">
                    {battle.winner_name ? `${battle.winner_name} won` : "awaiting vote"}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="mt-8 text-center text-xs text-[var(--color-muted)]" role="status">
        {healthLoading
          ? "Checking backend…"
          : health
            ? `Backend ${health.version} · Groq ${health.groq_model} / Gemini ${health.gemini_model} · TTS ${health.tts_provider}`
            : "Backend offline — start it with the README instructions."}
      </p>
    </AppShell>
  );
}