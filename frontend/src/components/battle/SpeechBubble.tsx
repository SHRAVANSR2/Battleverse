import type { Verse } from "../../types/api";
import { paletteFor, RobotAvatar, variantForName } from "../character/RobotAvatar";
import { Chip } from "../ui/Chip";
import { VerseAudioControls } from "../audio/VerseAudioControls";

export interface SpeechBubbleProps {
  verse: Verse;
  side: "left" | "right";
  speaking: boolean;
  onPlay: (verseId: string) => void;
  pending?: boolean;
  error?: string | null;
}

export function SpeechBubble({
  verse,
  side,
  speaking,
  onPlay,
  pending = false,
  error = null,
}: SpeechBubbleProps) {
  const palette = paletteFor(verse.accent);
  const lines = verse.verse_text.split("\n");

  return (
    <article
      className={`flex gap-3 ${side === "right" ? "flex-row-reverse" : ""}`}
      data-verse-id={verse.id}
      aria-label={`Verse ${verse.turn_number} by ${verse.character_name}`}
    >
      <div className="shrink-0 pt-1">
        <RobotAvatar
          accent={verse.accent}
          variant={variantForName(verse.character_name)}
          size={44}
          speaking={speaking}
        />
      </div>

      <div className="min-w-0 flex-1">
        <div
          className={`mb-1 flex flex-wrap items-center gap-2 text-xs text-[var(--color-muted)] ${
            side === "right" ? "justify-end" : ""
          }`}
        >
          <span className="font-bold text-[var(--color-ink)]">{verse.character_name}</span>
          <span>Round {verse.round_number}</span>
          {verse.is_demo ? (
            <Chip tone="demo" title="Demo Mode — scripted line, not AI-generated">
              demo
            </Chip>
          ) : null}
          {speaking ? (
            <span
              className="inline-flex items-center gap-1.5 font-semibold"
              style={{ color: palette.dark }}
            >
              <span className="bv-wave" aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
              </span>
              Speaking
            </span>
          ) : null}
        </div>

        <div
          className={`bv-transition relative rounded-3xl border px-4 py-3 shadow-[var(--shadow-soft)] ${
            speaking ? "ring-2" : ""
          }`}
          style={{
            borderColor: speaking ? palette.body : "var(--color-line)",
            backgroundColor: side === "right" ? palette.glow : "#ffffff",
            ...(speaking ? { ["--tw-ring-color" as string]: palette.body } : {}),
          }}
        >
          <p className="whitespace-pre-line text-[1.02rem] leading-relaxed">
            {lines.join("\n")}
          </p>

          <div
            className={`mt-2 flex items-center gap-2 ${
              side === "right" ? "justify-end" : ""
            }`}
          >
            <VerseAudioControls
              verseId={verse.id}
              accent={palette.body}
              speaking={speaking}
              pending={pending}
              error={error}
              onPlay={onPlay}
              hasAudio={Boolean(verse.audio)}
            />
          </div>
        </div>
      </div>
    </article>
  );
}