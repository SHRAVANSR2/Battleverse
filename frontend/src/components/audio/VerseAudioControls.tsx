import { Spinner } from "../ui/Button";

export interface VerseAudioControlsProps {
  verseId: string;
  accent: string;
  speaking: boolean;
  pending: boolean;
  error: string | null;
  hasAudio: boolean;
  onPlay: (verseId: string) => void;
}

/** Small per-bubble play/replay button. Replay never calls the turn endpoint. */
export function VerseAudioControls({
  verseId,
  accent,
  speaking,
  pending,
  error,
  hasAudio,
  onPlay,
}: VerseAudioControlsProps) {
  const label = speaking
    ? "Restart this line"
    : hasAudio
      ? "Replay this line"
      : "Speak this line";

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => onPlay(verseId)}
        disabled={pending}
        aria-label={label}
        title={label}
        className="bv-transition inline-flex min-h-[36px] items-center gap-1.5 rounded-full border border-[var(--color-line)] bg-white/80 px-3 text-xs font-semibold hover:bg-white disabled:opacity-60"
        style={{ color: accent }}
      >
        {pending ? (
          <Spinner label="Generating speech" />
        ) : (
          <span aria-hidden="true">{speaking ? "⟲" : "▶"}</span>
        )}
        {pending ? "Generating…" : speaking ? "Replay" : "Play"}
      </button>
      {error ? (
        <span role="alert" className="text-xs text-[var(--color-danger)]">
          {error}
        </span>
      ) : null}
    </div>
  );
}