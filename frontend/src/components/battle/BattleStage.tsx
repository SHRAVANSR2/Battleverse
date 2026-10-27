import { useEffect, useRef, useState } from "react";
import type { Character } from "../../types/api";
import { paletteFor, RobotAvatar, variantForName } from "../character/RobotAvatar";
import type { RobotMood } from "../character/RobotAvatar";

export interface BattleStageProps {
  fighterA: Character;
  fighterB: Character;
  topic: string;
  /** Character whose verse is being spoken right now (audio). */
  speakingCharacterId: string | null;
  /** Character whose verse is being written right now (LLM call in flight). */
  thinkingCharacterId: string | null;
  /** Author of the most recent verse. */
  lastSpeakerId: string | null;
  currentRound: number;
  roundCount: number;
  finished: boolean;
}

function moodFor(
  id: string,
  speakingId: string | null,
  thinkingId: string | null,
  lastSpeakerId: string | null,
): RobotMood {
  if (speakingId === id) return "speaking";
  if (thinkingId === id) return "thinking";
  if (speakingId && speakingId !== id) return "reacting";
  if (!thinkingId && lastSpeakerId && lastSpeakerId !== id) return "reacting";
  return "idle";
}

export function BattleStage({
  fighterA,
  fighterB,
  topic,
  speakingCharacterId,
  thinkingCharacterId,
  lastSpeakerId,
  currentRound,
  roundCount,
  finished,
}: BattleStageProps) {
  const fighters = [fighterA, fighterB];
  const nameOf = (id: string | null) => fighters.find((f) => f.id === id)?.name ?? "";

  // Slam-in banner the moment the round number ticks up. Purely cosmetic:
  // `aria-hidden` and pointer-transparent, never blocks interaction.
  const [slamRound, setSlamRound] = useState<number | null>(null);
  const seenRound = useRef(currentRound);
  useEffect(() => {
    if (currentRound > seenRound.current) {
      seenRound.current = currentRound;
      setSlamRound(currentRound);
      const timer = window.setTimeout(() => setSlamRound(null), 1400);
      return () => window.clearTimeout(timer);
    }
    seenRound.current = currentRound;
    return;
  }, [currentRound]);

  let caption = "Waiting for the opening bell…";
  if (speakingCharacterId) caption = `${nameOf(speakingCharacterId)} is on the mic`;
  else if (thinkingCharacterId) caption = `${nameOf(thinkingCharacterId)} is cooking up a comeback…`;
  else if (finished) caption = "Final bell! Time to pick a winner.";
  else if (lastSpeakerId) {
    const other = fighters.find((f) => f.id !== lastSpeakerId);
    caption = `${other?.name ?? "Your robot"} has to answer that one`;
  }

  return (
    <section className="bv-stage mb-5" aria-label="Battle stage">
      <div className="bv-stage-lights" aria-hidden="true" />

      {slamRound && !finished ? (
        <div className="bv-round-slam" aria-hidden="true">
          <span>
            Round {slamRound}
            {roundCount > 1 ? ` of ${roundCount}` : ""}
          </span>
        </div>
      ) : null}

      <div className="relative z-10 flex flex-wrap items-center justify-between gap-2 px-4 pt-4 sm:px-6">
        <span className="bv-neon-sign" title="Battle topic">
          <span className="opacity-70">Topic</span> · {topic}
        </span>
        <div className="flex items-center gap-1.5" aria-label={`Round ${currentRound} of ${roundCount}`}>
          {Array.from({ length: roundCount }, (_, i) => {
            const n = i + 1;
            const state = finished || n < currentRound ? "done" : n === currentRound ? "now" : "next";
            return (
              <span key={n} className={`bv-pip bv-pip-${state}`}>
                R{n}
              </span>
            );
          })}
        </div>
      </div>

      <div className="relative z-10 grid grid-cols-[1fr_auto_1fr] items-end gap-1 px-2 pb-3 pt-2 sm:gap-4 sm:px-8">
        <Fighter
          character={fighterA}
          mood={moodFor(fighterA.id, speakingCharacterId, thinkingCharacterId, lastSpeakerId)}
          side="left"
        />
        <div className="bv-vs" aria-hidden="true">
          VS
        </div>
        <Fighter
          character={fighterB}
          mood={moodFor(fighterB.id, speakingCharacterId, thinkingCharacterId, lastSpeakerId)}
          side="right"
        />
      </div>

      <p className="bv-stage-caption relative z-10" role="status" aria-live="polite">
        {caption}
      </p>
    </section>
  );
}

function Fighter({
  character,
  mood,
  side,
}: {
  character: Character;
  mood: RobotMood;
  side: "left" | "right";
}) {
  const palette = paletteFor(character.accent);
  const active = mood === "speaking" || mood === "thinking";
  return (
    <div
      className={`bv-fighter ${active ? "bv-fighter-active" : ""}`}
      style={{ ["--accent" as string]: palette.body, ["--accent-soft" as string]: palette.glow }}
      aria-current={active ? "true" : undefined}
      data-mood={mood}
    >
      <div className="bv-fighter-robot">
        <RobotAvatar
          accent={character.accent}
          variant={variantForName(character.name)}
          size={150}
          mood={mood}
          className={side === "right" ? "bv-flip" : ""}
        />
        <span className="bv-spot" aria-hidden="true" />
      </div>
      <div className="bv-nameplate">
        <span className="bv-nameplate-name">{character.name}</span>
        <span className="bv-nameplate-tag" title={character.tagline}>
          {mood === "speaking" ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="bv-wave" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
              On the mic
            </span>
          ) : mood === "thinking" ? (
            "Writing bars…"
          ) : (
            character.tagline
          )}
        </span>
      </div>
    </div>
  );
}