import { Fragment, useEffect, useMemo, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { BattleStage } from "../components/battle/BattleStage";
import { SpeechBubble } from "../components/battle/SpeechBubble";
import { AudioBar } from "../components/audio/AudioBar";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { Chip } from "../components/ui/Chip";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingBlock } from "../components/ui/LoadingBlock";
import { useAudio } from "../audio/AudioProvider";
import { useRapBeat } from "../hooks/useRapBeat";
import { useBattle } from "../hooks/useBattle";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { RobotAvatar, variantForName } from "../components/character/RobotAvatar";
import { VotingPanel } from "../components/battle/VotingPanel";

export function BattleArenaPage() {
  const { battleId } = useParams<{ battleId: string }>();
  const { battle, loading, generating, error, canRetry, generateTurn, runAuto, stopAuto, autoRunning, refresh } =
    useBattle(battleId);
  const audio = useAudio();
  const autoStarted = useRef(false);
  /** True once this page visit has started a live auto battle (not a replay of an old one). */
  const liveAuto = useRef(false);
  const lastAutoSpoken = useRef<string | null>(null);

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
    liveAuto.current = true;
    void runAuto();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [battle?.id, battle?.playback_mode]);

  // Auto mode: speak every verse in order, hands-free. The audio queue chains
  // verses that are already waiting; this covers the first verse and any verse
  // that lands after the previous one has finished (a slow turn).
  useEffect(() => {
    if (!battle || battle.playback_mode !== "auto" || !liveAuto.current) return;
    const a = audio.state;
    if (!a.autoplay || a.stoppedByUser || a.mode !== "idle") return;
    const next = a.queue.find((item) => item.state === "queued");
    if (!next || lastAutoSpoken.current === next.verseId) return;
    lastAutoSpoken.current = next.verseId;
    void audio.playVerse(next.verseId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [battle?.playback_mode, audio.state.mode, audio.state.queue, audio.state.autoplay, audio.state.stoppedByUser]);

  // Keep the newest line in view as the exchange grows.
  const endRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (allVerses.length === 0) return;
    endRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [allVerses.length, generating]);

  const speakingId = useMemo(() => {
    const verse = allVerses.find((item) => audio.isSpeaking(item.id));
    return verse?.id ?? null;
  }, [allVerses, audio]);

  // Backing beat: matches the battle style, only while a verse is spoken.
  const beat = useRapBeat({
    style: battle?.style ?? "rap",
    speaking: audio.state.mode === "playing" && Boolean(audio.state.activeVerseId),
    muted: audio.state.muted,
    volume: audio.state.volume,
  });

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
  const speakingVerse = allVerses.find((v) => v.id === speakingId) ?? null;
  const nextSpeaker = battle.next_turn_number % 2 === 1 ? fighterA : fighterB;
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

      <BattleStage
        fighterA={fighterA}
        fighterB={fighterB}
        topic={battle.topic}
        speakingCharacterId={speakingVerse?.character_id ?? null}
        thinkingCharacterId={generating ? nextSpeaker.id : null}
        lastSpeakerId={allVerses.length > 0 ? allVerses[allVerses.length - 1]!.character_id : null}
        currentRound={Math.min(battle.round_count, Math.max(1, Math.ceil(battle.next_turn_number / 2)))}
        roundCount={battle.round_count}
        finished={finished}
      />

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

      <section aria-label="Battle transcript" className="bv-ring">
        <div className="flex flex-col gap-4">
          {allVerses.map((verse, index) => {
            const isA = verse.character_id === fighterA.id;
            const newRound = index === 0 || allVerses[index - 1]!.round_number !== verse.round_number;
            return (
              <Fragment key={verse.id}>
                {newRound ? (
                  <div className="bv-round-divider" role="separator" aria-label={`Round ${verse.round_number}`}>
                    <span>Round {verse.round_number}</span>
                  </div>
                ) : null}
                <SpeechBubble
                  verse={verse}
                  side={isA ? "left" : "right"}
                  speaking={audio.isSpeaking(verse.id)}
                  pending={audio.pendingFor(verse.id)}
                  error={audio.errorFor(verse.id)}
                  onPlay={(id) => void audio.playVerse(id)}
                />
              </Fragment>
            );
          })}

          {generating ? (
            <div
              className={`flex items-center gap-3 ${nextSpeaker.id === fighterB.id ? "flex-row-reverse" : ""}`}
              role="status"
              aria-label={`${nextSpeaker.name} is writing a verse`}
            >
              <RobotAvatar
                accent={nextSpeaker.accent}
                variant={variantForName(nextSpeaker.name)}
                size={52}
                mood="thinking"
              />
              <span className="bv-typing" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
            </div>
          ) : null}
          <div ref={endRef} />
        </div>

        {allVerses.length === 0 && !generating ? (
          <p className="m-0 py-6 text-center text-sm text-slate-400">
            The ring is quiet. Ring the bell to start the battle.
          </p>
        ) : null}
      </section>

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
        {beat.supported ? (
          <button
            type="button"
            onClick={beat.toggle}
            aria-pressed={beat.enabled}
            className="bv-card bv-transition flex items-center gap-2 px-4 py-2 text-sm font-semibold hover:shadow-[var(--shadow-soft)]"
          >
            <span aria-hidden="true">🥁</span>
            Beat: {beat.enabled ? "On" : "Off"}
            <span className="text-xs font-normal text-[var(--color-muted)]">
              plays under {battle?.style ?? "rap"} verses
            </span>
          </button>
        ) : null}
      </div>
    </AppShell>
  );
}