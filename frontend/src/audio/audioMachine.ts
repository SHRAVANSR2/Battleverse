/**
 * Pure audio queue state machine.
 *
 * One hidden <audio> element plays one item at a time. This reducer owns the
 * queue; the provider owns side effects. Keeping it pure makes the tricky parts
 * (dedupe, pause vs. advance, stop-all, strict-mode double invocation) testable
 * without a DOM.
 */

export type ItemState = "queued" | "loading" | "playing" | "paused" | "ready" | "failed";

export type AudioMode = "idle" | "generating" | "playing" | "paused" | "blocked";

export interface QueueItem {
  verseId: string;
  src: string | null;
  state: ItemState;
  error: string | null;
}

export interface AudioState {
  mode: AudioMode;
  queue: QueueItem[];
  activeVerseId: string | null;
  muted: boolean;
  volume: number;
  autoplay: boolean;
  /** Set when the browser refused play(); the UI shows a tap-to-start banner. */
  blockedReason: string | null;
  lastError: string | null;
  /**
   * True after the listener pressed Stop. Auto mode must not start speaking
   * again by itself until they press Play on something.
   */
  stoppedByUser: boolean;
}

export type AudioAction =
  | { type: "ENQUEUE"; items: { verseId: string; src?: string | null }[] }
  | { type: "REPLACE_QUEUE"; items: { verseId: string; src?: string | null }[] }
  | { type: "PLAY"; verseId: string }
  | { type: "LOADING"; verseId: string }
  | { type: "PLAYING"; verseId: string }
  | { type: "PAUSED"; verseId: string }
  | { type: "ENDED"; verseId: string }
  | { type: "SET_SRC"; verseId: string; src: string }
  | { type: "FAILED"; verseId: string; message: string }
  | { type: "ADVANCE" }
  | { type: "STOP_ALL" }
  | { type: "BLOCKED"; reason: string }
  | { type: "CLEAR_BLOCKED" }
  | { type: "SET_MUTED"; muted: boolean }
  | { type: "SET_VOLUME"; volume: number }
  | { type: "SET_AUTOPLAY"; autoplay: boolean }
  | { type: "ERROR"; message: string | null };

export const initialAudioState: AudioState = {
  mode: "idle",
  queue: [],
  activeVerseId: null,
  muted: false,
  volume: 0.9,
  autoplay: true,
  blockedReason: null,
  lastError: null,
  stoppedByUser: false,
};

const IN_FLIGHT: ItemState[] = ["queued", "loading", "playing", "paused"];

function hasItem(state: AudioState, verseId: string): boolean {
  return state.queue.some((item) => item.verseId === verseId);
}

function makeItem(verseId: string, src?: string | null): QueueItem {
  return { verseId, src: src ?? null, state: "queued", error: null };
}

function nextPlayable(queue: QueueItem[], afterId: string | null): QueueItem | null {
  const start = afterId ? queue.findIndex((item) => item.verseId === afterId) : -1;
  for (let index = start + 1; index < queue.length; index += 1) {
    const item = queue[index];
    if (item && item.state !== "failed") return item;
  }
  return null;
}

/** The item to auto-play after `verseId` finished, only if autoplay is on. */
export function pickNext(state: AudioState): QueueItem | null {
  if (!state.autoplay) return null;
  return nextPlayable(state.queue, state.activeVerseId);
}

export function audioReducer(state: AudioState, action: AudioAction): AudioState {
  switch (action.type) {
    case "ENQUEUE": {
      const additions = action.items
        .filter((entry) => !hasItem(state, entry.verseId))
        .map((entry) => makeItem(entry.verseId, entry.src));
      if (additions.length === 0) return state;
      return { ...state, queue: [...state.queue, ...additions] };
    }

    case "REPLACE_QUEUE": {
      // Sync the queue with the transcript WITHOUT disturbing playback.
      // In auto mode new verses arrive while another is being spoken; wiping
      // the active item (or its fetched audio URL) here used to strand the
      // next robot on "Generating…" forever.
      const existing = new Map(state.queue.map((item) => [item.verseId, item]));
      const items = action.items.map((entry) => {
        const kept = existing.get(entry.verseId);
        if (!kept) return makeItem(entry.verseId, entry.src);
        return kept.src || !entry.src ? kept : { ...kept, src: entry.src };
      });
      const activeStillThere =
        state.activeVerseId !== null && items.some((item) => item.verseId === state.activeVerseId);
      return {
        ...state,
        queue: items,
        activeVerseId: activeStillThere ? state.activeVerseId : null,
        mode: activeStillThere || state.mode === "idle" || state.mode === "blocked" ? state.mode : "idle",
      };
    }

    case "PLAY": {
      // An explicit user play resumes the active item or switches to another.
      // Mode stays "generating" until the element fires a real `playing` event,
      // so the Speaking highlight always reflects actual audio output.
      return {
        ...state,
        mode: "generating",
        activeVerseId: action.verseId,
        blockedReason: null,
        lastError: null,
        stoppedByUser: false,
        queue: state.queue.map((item) =>
          item.verseId === action.verseId
            ? { ...item, state: item.state === "paused" ? "paused" : "loading", error: null }
            : item.state === "playing"
              ? { ...item, state: "ready" }
              : item,
        ),
      };
    }

    case "LOADING":
      return {
        ...state,
        mode: "generating",
        queue: state.queue.map((item) =>
          item.verseId === action.verseId ? { ...item, state: "loading" } : item,
        ),
      };

    case "SET_SRC":
      return {
        ...state,
        queue: state.queue.map((item) =>
          item.verseId === action.verseId ? { ...item, src: action.src } : item,
        ),
      };

    case "PLAYING":
      return {
        ...state,
        mode: "playing",
        activeVerseId: action.verseId,
        blockedReason: null,
        lastError: null,
        queue: state.queue.map((item) =>
          item.verseId === action.verseId ? { ...item, state: "playing", error: null } : item,
        ),
      };

    case "PAUSED":
      return {
        ...state,
        mode: "paused",
        queue: state.queue.map((item) =>
          item.verseId === action.verseId ? { ...item, state: "paused" } : item,
        ),
      };

    case "ENDED":
      return {
        ...state,
        mode: "idle",
        queue: state.queue.map((item) =>
          item.verseId === action.verseId ? { ...item, state: "ready" } : item,
        ),
      };

    case "ADVANCE": {
      // Nothing is active (e.g. the listener pressed Stop): never restart from the top.
      if (state.activeVerseId === null) return state;
      const upcoming = nextPlayable(state.queue, state.activeVerseId);
      if (!upcoming) {
        return { ...state, mode: "idle", activeVerseId: null };
      }
      return {
        ...state,
        mode: "playing",
        activeVerseId: upcoming.verseId,
        queue: state.queue.map((item) =>
          item.verseId === upcoming.verseId ? { ...item, state: "loading" } : item,
        ),
      };
    }

    case "FAILED":
      return {
        ...state,
        lastError: action.message,
        queue: state.queue.map((item) =>
          item.verseId === action.verseId
            ? { ...item, state: "failed", error: action.message }
            : item,
        ),
      };

    case "STOP_ALL":
      return {
        ...state,
        mode: "idle",
        activeVerseId: null,
        blockedReason: null,
        stoppedByUser: true,
        queue: state.queue.map((item) =>
          IN_FLIGHT.includes(item.state) ? { ...item, state: "ready" } : item,
        ),
      };

    case "BLOCKED":
      return { ...state, mode: "blocked", blockedReason: action.reason };

    case "CLEAR_BLOCKED":
      return { ...state, blockedReason: null, mode: state.mode === "blocked" ? "idle" : state.mode };

    case "SET_MUTED":
      return { ...state, muted: action.muted };

    case "SET_VOLUME":
      return { ...state, volume: Math.min(1, Math.max(0, action.volume)) };

    case "SET_AUTOPLAY":
      return { ...state, autoplay: action.autoplay };

    case "ERROR":
      return { ...state, lastError: action.message, mode: action.message ? state.mode : state.mode };

    default:
      return state;
  }
}