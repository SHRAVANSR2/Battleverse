import { useEffect, useMemo, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { FighterCard } from "../components/battle/FighterCard";
import { SpeechBubble } from "../components/battle/SpeechBubble";
import { AudioBar } from "../components/audio/AudioBar";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { Chip } from "../components/ui/Chip";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingBlock } from "../components/ui/LoadingBlock";
import { useAudio } from "../audio/AudioProvider";
import { useBattle } from "../hooks/useBattle";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { VotingPanel } from "../components/battle/VotingPanel";

export function BattleArenaPage() {
  const { battleId } = useParams<{ battleId: string }>();
  const { battle, loading, generating, error, canRetry, generateTurn, runAuto, stopAuto, autoRunning, refresh } =
    useBattle(battleId);
  const audio = useAudio();
  const autoStarted = useRef(false);

  useDocumentTitle(battle ? `${battle.fighter_a.name} vs ${battle.fighter_b.name}` : "Battle");

  const allVerses = battle?.verses ?? [];

  // Keep the audio queue in sync with the transcript without restarting playback.
  useEffect(() => {
    audio.queueVerses(allVerses);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allVerses.length]);

  // Auto playback mode: generate every turn once the page opens.
  useEffect(() => {
    if (!battle) return;
    if (battle.playback_mode !== "auto") return;
    if (battle.status !== "in_progress" && battle.status !== "created") return;
    if (autoStarted.current) return;
    autoStarted.current = true;
    void runAuto();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [battle?.id, battle?.playback_mode]);

  const speakingId = useMemo(() => {
    const verse = allVerses.find((item) => audio.isSpeaking(item.id));
    return verse?.id ?? null;
  }, [allVerses, audio]);

  if (loading && !battle) {
    return (
      <AppShell>
        <LoadingBlock label="Rolling out the arena…" />
      </AppShell>
    );
  }

  if (!battle) {
    return (
      <AppShell>
        <ErrorState
          message={error?.message ?? "This battle could not be found."}
          code={error?.code}
          onRetry={() => void refresh()}
        />
        <p className="mt-4 text-center">
          <Link to="/battle/new" className="font-semibold text-[var(--color-primary-ink)]">
            Start a new battle
          </Link>
        </p>
      </AppShell>
    );
  }

  const fighterA = battle.fighter_a;
  const fighterB = battle.fighter_b;
  const inProgress = battle.status === "in_progress" || battle.status === "created";
  const finished = battle.status === "awaiting_vote" || battle.status === "completed";

  return (
    <AppShell>
      <PageHeader
        title={`${fighterA.name} vs ${fighterB.name}`}
        subtitle={
          <>
            <Chip tone="accent">Topic</Chip>{" "}
            <span className="font-medium text-[var(--color-ink)]">{battle.topic}</span> ·{" "}
            {battle.round_count} {battle.round_count === 1 ? "round" : "rounds"} ·{" "}
            {battle.style} · {battle.intensity}
          </>
        }
        actions={
          <Link
            to="/history"
            className="text-sm font-semibold text-[var(--color-primary-ink)] no-underline hover:underline"
          >
            Battle history →
          </Link>
        }
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <FighterCard
          character={fighterA}
          side="left"
          speaking={speakingId !== null && allVerses.find((v) => v.id === speakingId)?.character_id === fighterA.id}
          active={speakingId !== null && allVerses.find((v) => v.id === speakingId)?.character_id === fighterA.id}
        />
        <FighterCard
          character={fighterB}
          side="right"
          speaking={speakingId !== null && allVerses.find((v) => v.id === speakingId)?.character_id === fighterB.id}
          active={speakingId !== null && allVerses.find((v) => v.id === speakingId)?.character_id === fighterB.id}
        />
      </div>

      {battle.playback_mode === "auto" && inProgress ? (
        <Banner tone="info" className="mb-4">
          Auto mode is generating every turn. You can stop it at any time.
          {autoRunning ? (
            <Button size="sm" variant="secondary" onClick={stopAuto} className="mt-2">
              Stop generating
            </Button>
          ) : null}
        </Banner>
      ) : null}

      {error ? (
        <Banner tone="danger" role="alert" className="mb-4">
          <span className="font-semibold">{error.message}</span>
          {error.code === "LLM_RATE_LIMITED" ? (
            <span className="block text-xs opacity-80">
              This is Groq's free-tier limit, not a bug. Wait a few seconds and retry.
            </span>
          ) : null}
          {canRetry ? (
            <Button
              size="sm"
              variant="secondary"
              className="mt-2"
              onClick={() => void generateTurn()}
              busy={generating}
            >
              Retry turn
            </Button>
          ) : null}
        </Banner>
      ) : null}

      <section aria-label="Battle transcript" className="grid gap-4 sm:grid-cols-2">
        <Column
          title={fighterA.name}
          verses={allVerses.filter((v) => v.character_id === fighterA.id)}
          side="left"
          audio={audio}
        />
        <Column
          title={fighterB.name}
          verses={allVerses.filter((v) => v.character_id === fighterB.id)}
          side="right"
          audio={audio}
        />
      </section>

      {allVerses.length === 0 ? (
        <div className="bv-card mx-auto mt-4 max-w-lg px-6 py-10 text-center">
          <p className="text-sm text-[var(--color-muted)]">
            No verses yet. Press <strong>Generate next turn</strong> to let{" "}
            {fighterA.name} open the battle.
          </p>
        </div>
      ) : null}

      <div className="mt-5 grid gap-3">
        {inProgress ? (
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="primary"
              size="lg"
              onClick={() => void generateTurn()}
              busy={generating}
              disabled={autoRunning}
            >
              {allVerses.length === 0
                ? `Let ${fighterA.name} start`
                : `Generate turn ${battle.next_turn_number}`}
            </Button>
            <span className="text-sm text-[var(--color-muted)]">
              Round {Math.max(1, Math.ceil(battle.next_turn_number / 2))} of{" "}
              {battle.round_count} · {allVerses.length}/{battle.total_turns} verses
            </span>
            {battle.playback_mode === "auto" && !autoRunning ? (
              <Button variant="secondary" size="sm" onClick={() => void runAuto()}>
                Resume auto-run
              </Button>
            ) : null}
          </div>
        ) : null}

        {finished ? <VotingPanel battle={battle} onDecided={() => void refresh()} /> : null}

        {allVerses.length > 0 ? <AudioBar /> : null}
      </div>
    </AppShell>
  );
}

function Column({
  title,
  verses,
  side,
  audio,
}: {
  title: string;
  verses: import("../types/api").Verse[];
  side: "left" | "right";
  audio: ReturnType<typeof useAudio>;
}) {
  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-bold uppercase tracking-wide text-[var(--color-muted)]">
        {title}
      </h2>
      {verses.map((verse) => (
        <SpeechBubble
          key={verse.id}
          verse={verse}
          side={side}
          speaking={audio.isSpeaking(verse.id)}
          pending={audio.pendingFor(verse.id)}
          error={audio.errorFor(verse.id)}
          onPlay={(id) => void audio.playVerse(id)}
        />
      ))}
    </div>
  );
}