import { useCallback, useEffect, useRef, useState } from "react";
import { BeatEngine, beatSupported } from "../audio/beat";
import type { BeatProfile } from "../audio/beat";
import type { BattleStyle } from "../types/api";

const STYLE_TO_PROFILE: Record<BattleStyle, BeatProfile> = {
  rap: "rap",
  roast: "roast",
  debate: "debate",
};

const STORAGE_KEY = "battleverse.beat";
/** Keeps the beat rolling through the short gap between two verses. */
const GAP_GRACE_MS = 1800;

function readEnabled(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) !== "off";
  } catch {
    return true;
  }
}

export interface RapBeat {
  supported: boolean;
  enabled: boolean;
  toggle: () => void;
}

/**
 * Plays a backing beat under spoken verses. The pattern follows the battle
 * style (rap = boom-bap, roast = lazy kick-snare, debate = ticking clock).
 * `speaking` should be true only while real speech audio is playing.
 */
export function useRapBeat(opts: {
  style: BattleStyle;
  speaking: boolean;
  muted: boolean;
  volume: number;
}): RapBeat {
  const { style, speaking, muted, volume } = opts;
  const [enabled, setEnabled] = useState<boolean>(readEnabled);
  const engine = useRef<BeatEngine | null>(null);
  const graceTimer = useRef<number | null>(null);
  const supported = beatSupported();

  const level = 0.22 * Math.min(1, Math.max(0, volume));
  const profile = STYLE_TO_PROFILE[style];
  const shouldPlay = supported && enabled && !muted && volume > 0;

  useEffect(() => {
    if (!shouldPlay) {
      engine.current?.stop();
      return;
    }
    if (!engine.current) engine.current = new BeatEngine();
    const beat = engine.current;

    if (speaking) {
      if (graceTimer.current !== null) {
        window.clearTimeout(graceTimer.current);
        graceTimer.current = null;
      }
      beat.start(level, profile);
    } else if (beat.running && graceTimer.current === null) {
      graceTimer.current = window.setTimeout(() => {
        graceTimer.current = null;
        beat.stop();
      }, GAP_GRACE_MS);
    }
  }, [shouldPlay, speaking, level, profile]);

  useEffect(() => {
    engine.current?.setLevel(level);
  }, [level]);

  useEffect(
    () => () => {
      if (graceTimer.current !== null) window.clearTimeout(graceTimer.current);
      engine.current?.dispose();
      engine.current = null;
    },
    [],
  );

  const toggle = useCallback(() => {
    setEnabled((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(STORAGE_KEY, next ? "on" : "off");
      } catch {
        /* storage unavailable: the choice just won't persist */
      }
      return next;
    });
  }, []);

  return { supported, enabled, toggle };
}