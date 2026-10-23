import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  type ReactNode,
} from "react";
import { ApiError } from "../services/client";
import { requestVerseAudio } from "../services/audio";
import type { Verse } from "../types/api";
import {
  audioReducer,
  initialAudioState,
  pickNext,
  type AudioState,
} from "./audioMachine";

const MUTE_KEY = "battleverse.muted";
const VOLUME_KEY = "battleverse.volume";
const AUTOPLAY_KEY = "battleverse.autoplay";

interface AudioApi {
  state: AudioState;
  /** Play a verse (fetches audio if needed). Must originate from a user gesture. */
  playVerse: (verseId: string) => Promise<void>;
  /** Queue verses for autoplay after the current one finishes. */
  queueVerses: (verses: Verse[]) => void;
  pause: () => void;
  resume: () => Promise<void>;
  replay: () => Promise<void>;
  stop: () => void;
  toggleMute: () => void;
  setVolume: (value: number) => void;
  setAutoplay: (value: boolean) => void;
  isSpeaking: (verseId: string) => boolean;
  isActive: (verseId: string) => boolean;
  pendingFor: (verseId: string) => boolean;
  errorFor: (verseId: string) => string | null;
}

const AudioContext = createContext<AudioApi | null>(null);

function readNumber(key: string, fallback: number): number {
  try {
    const raw = window.localStorage.getItem(key);
    const parsed = raw === null ? NaN : Number.parseFloat(raw);
    return Number.isFinite(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

function readBool(key: string, fallback: boolean): boolean {
  try {
    const raw = window.localStorage.getItem(key);
    return raw === null ? fallback : raw === "true";
  } catch {
    return fallback;
  }
}

function persist(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* storage may be unavailable in private mode */
  }
}

export function AudioProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(audioReducer, initialAudioState, (base) => ({
    ...base,
    muted: readBool(MUTE_KEY, false),
    volume: Math.min(1, Math.max(0, readNumber(VOLUME_KEY, 0.9))),
    autoplay: readBool(AUTOPLAY_KEY, true),
  }));

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const stateRef = useRef(state);
  stateRef.current = state;
  const fetchControllers = useRef(new Map<string, AbortController>());

  // --- the single hidden audio element -----------------------------------
  useEffect(() => {
    const element = new Audio();
    element.preload = "auto";
    audioRef.current = element;

    const onPlaying = () => {
      const verseId = stateRef.current.activeVerseId;
      if (verseId) dispatch({ type: "PLAYING", verseId });
    };
    const onPause = () => {
      const verseId = stateRef.current.activeVerseId;
      if (!verseId) return;
      if (element.ended) return;
      dispatch({ type: "PAUSED", verseId });
    };
    const onEnded = () => {
      const verseId = stateRef.current.activeVerseId;
      if (verseId) dispatch({ type: "ENDED", verseId });
      const next = pickNext(stateRef.current);
      if (next) {
        dispatch({ type: "ADVANCE" });
      }
    };
    const onError = () => {
      const verseId = stateRef.current.activeVerseId;
      if (verseId) {
        dispatch({
          type: "FAILED",
          verseId,
          message: "This audio clip could not be played. Try regenerating it.",
        });
      }
    };

    element.addEventListener("playing", onPlaying);
    element.addEventListener("pause", onPause);
    element.addEventListener("ended", onEnded);
    element.addEventListener("error", onError);

    return () => {
      element.removeEventListener("playing", onPlaying);
      element.removeEventListener("pause", onPause);
      element.removeEventListener("ended", onEnded);
      element.removeEventListener("error", onError);
      element.pause();
      element.removeAttribute("src");
      element.load();
      audioRef.current = null;
    };
  }, []);

  // Apply volume/mute to the element.
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.muted = state.muted;
      audioRef.current.volume = state.volume;
    }
  }, [state.muted, state.volume]);

  // Load the active item's src and play it. Keyed on (activeVerseId, src) so a
  // newly fetched URL starts playback without needing a second user action.
  const activeSrc = useMemo(() => {
    const item = state.queue.find((entry) => entry.verseId === state.activeVerseId);
    return item?.src ?? null;
  }, [state.queue, state.activeVerseId]);

  useEffect(() => {
    const element = audioRef.current;
    const activeId = state.activeVerseId;
    if (!element || !activeId || !activeSrc) return;

    if (!element.src.endsWith(activeSrc)) {
      element.src = activeSrc;
      element.load();
    }
    element.muted = state.muted;
    element.volume = state.volume;
    void element.play().catch((err: unknown) => {
      const name = err instanceof DOMException ? err.name : "";
      if (name === "NotAllowedError") {
        dispatch({
          type: "BLOCKED",
          reason: "Your browser needs a tap before it will play audio.",
        });
      } else if (name !== "AbortError") {
        dispatch({
          type: "FAILED",
          verseId: activeId,
          message: "Audio could not start. Please tap play again.",
        });
      }
    });
    // muted/volume are applied by their own effect; re-running there would restart audio.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.activeVerseId, activeSrc]);

  const ensureSrc = useCallback(async (verseId: string): Promise<string | null> => {
    const existing = stateRef.current.queue.find((item) => item.verseId === verseId);
    if (existing?.src) return existing.src;

    const controller = new AbortController();
    fetchControllers.current.set(verseId, controller);
    try {
      const asset = await requestVerseAudio(verseId, controller.signal);
      if (!asset.url) throw new ApiError("No audio URL was returned.");
      dispatch({ type: "SET_SRC", verseId, src: asset.url });
      return asset.url;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return null;
      const message =
        err instanceof ApiError
          ? err.message
          : "We could not generate speech for this verse.";
      dispatch({ type: "FAILED", verseId, message });
      return null;
    } finally {
      fetchControllers.current.delete(verseId);
    }
  }, []);

  const playVerse = useCallback(
    async (verseId: string) => {
      dispatch({ type: "PLAY", verseId });
      // The source effect picks it up as soon as SET_SRC lands in state.
      const src = await ensureSrc(verseId);
      if (!src) {
        dispatch({ type: "ADVANCE" });
      }
    },
    [ensureSrc],
  );

  const queueVerses = useCallback((verses: Verse[]) => {
    dispatch({
      type: "REPLACE_QUEUE",
      items: verses.map((verse) => ({
        verseId: verse.id,
        src: verse.audio?.url ?? null,
      })),
    });
  }, []);

  const pause = useCallback(() => {
    audioRef.current?.pause();
  }, []);

  const resume = useCallback(async () => {
    const element = audioRef.current;
    const activeId = stateRef.current.activeVerseId;
    if (!element || !activeId) return;
    dispatch({ type: "CLEAR_BLOCKED" });
    try {
      await element.play();
    } catch {
      const src = await ensureSrc(activeId);
      if (src) {
        element.src = src;
        try {
          await element.play();
        } catch {
          dispatch({ type: "BLOCKED", reason: "Tap play to allow audio." });
        }
      }
    }
  }, [ensureSrc]);

  const replay = useCallback(async () => {
    const element = audioRef.current;
    const activeId = stateRef.current.activeVerseId;
    if (!element || !activeId) return;
    element.currentTime = 0;
    try {
      await element.play();
    } catch {
      await resume();
    }
  }, [resume]);

  const stop = useCallback(() => {
    for (const controller of fetchControllers.current.values()) controller.abort();
    fetchControllers.current.clear();
    const element = audioRef.current;
    if (element) {
      element.pause();
      element.removeAttribute("src");
      element.load();
    }
    dispatch({ type: "STOP_ALL" });
  }, []);

  const toggleMute = useCallback(() => {
    const next = !stateRef.current.muted;
    persist(MUTE_KEY, String(next));
    dispatch({ type: "SET_MUTED", muted: next });
  }, []);

  const setVolume = useCallback((value: number) => {
    const clamped = Math.min(1, Math.max(0, value));
    persist(VOLUME_KEY, String(clamped));
    dispatch({ type: "SET_VOLUME", volume: clamped });
    if (clamped > 0 && stateRef.current.muted) {
      persist(MUTE_KEY, "false");
      dispatch({ type: "SET_MUTED", muted: false });
    }
  }, []);

  const setAutoplay = useCallback((value: boolean) => {
    persist(AUTOPLAY_KEY, String(value));
    dispatch({ type: "SET_AUTOPLAY", autoplay: value });
  }, []);

  // Stop playback when the tab is hidden for a long time is intentionally NOT done:
  // pausing on tab switch would break "keep listening while browsing".

  const api = useMemo<AudioApi>(
    () => ({
      state,
      playVerse,
      queueVerses,
      pause,
      resume,
      replay,
      stop,
      toggleMute,
      setVolume,
      setAutoplay,
      // Only true while the <audio> element is genuinely emitting sound.
      isSpeaking: (verseId) => state.activeVerseId === verseId && state.mode === "playing",
      isActive: (verseId) => state.activeVerseId === verseId,
      pendingFor: (verseId) =>
        state.queue.find((item) => item.verseId === verseId)?.state === "loading",
      errorFor: (verseId) =>
        state.queue.find((item) => item.verseId === verseId)?.error ?? null,
    }),
    [
      state,
      playVerse,
      queueVerses,
      pause,
      resume,
      replay,
      stop,
      toggleMute,
      setVolume,
      setAutoplay,
    ],
  );

  return <AudioContext.Provider value={api}>{children}</AudioContext.Provider>;
}

export function useAudio(): AudioApi {
  const context = useContext(AudioContext);
  if (context === null) {
    throw new Error("useAudio must be used inside <AudioProvider>");
  }
  return context;
}