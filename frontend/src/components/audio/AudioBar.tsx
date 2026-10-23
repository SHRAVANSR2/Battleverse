import { useAudio } from "../../audio/AudioProvider";
import { Button } from "../ui/Button";

/** Global playback controls under the transcript. */
export function AudioBar() {
  const audio = useAudio();
  const { state } = audio;
  // Pause stays available while a clip is loading so it can be cancelled.
  const canPause =
    Boolean(state.activeVerseId) && (state.mode === "playing" || state.mode === "generating");
  const isPaused = state.mode === "paused";
  const hasActive = Boolean(state.activeVerseId);

  return (
    <div
      className="bv-card flex flex-wrap items-center gap-3 px-4 py-3"
      role="group"
      aria-label="Playback controls"
    >
      {isPaused ? (
        <Button variant="primary" size="sm" onClick={() => void audio.resume()}>
          <span aria-hidden="true">▶</span> Resume
        </Button>
      ) : (
        <Button
          variant="secondary"
          size="sm"
          onClick={audio.pause}
          disabled={!canPause}
          aria-label="Pause playback"
        >
          <span aria-hidden="true">⏸</span> Pause
        </Button>
      )}

      <Button
        variant="secondary"
        size="sm"
        onClick={() => void audio.replay()}
        disabled={!hasActive}
        aria-label="Replay the current line"
      >
        <span aria-hidden="true">⟲</span> Replay
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={audio.toggleMute}
        aria-pressed={state.muted}
        aria-label={state.muted ? "Unmute audio" : "Mute audio"}
      >
        <span aria-hidden="true">{state.muted ? "🔇" : "🔊"}</span>
        {state.muted ? "Muted" : "Mute"}
      </Button>

      <label className="flex items-center gap-2 text-sm text-[var(--color-muted)]">
        <span className="sr-only">Volume</span>
        <span aria-hidden="true">🔉</span>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={Math.round(state.volume * 100)}
          onChange={(event) => audio.setVolume(Number(event.target.value) / 100)}
          className="h-2 w-24 cursor-pointer accent-[var(--color-primary)]"
          aria-label="Volume"
        />
      </label>

      <label className="ml-auto flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={state.autoplay}
          onChange={(event) => audio.setAutoplay(event.target.checked)}
          className="size-4 accent-[var(--color-primary)]"
        />
        Autoplay
      </label>

      <Button
        variant="ghost"
        size="sm"
        onClick={audio.stop}
        disabled={!hasActive}
        aria-label="Stop playback and clear the queue"
      >
        <span aria-hidden="true">⏹</span> Stop
      </Button>

      <p className="basis-full text-xs text-[var(--color-muted)]" role="status" aria-live="polite">
        {state.lastError
          ? state.lastError
          : state.mode === "blocked"
            ? (state.blockedReason ?? "Tap play to allow audio.")
            : ""}
      </p>
    </div>
  );
}