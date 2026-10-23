import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../services/client";
import { fetchBattle, takeTurn } from "../services/battles";
import type { BattleDetail, TurnResponse } from "../types/api";

const RETRYABLE_STATUS = new Set(["LLM_UNAVAILABLE", "LLM_TIMEOUT", "LLM_RATE_LIMITED"]);

export interface BattleState {
  battle: BattleDetail | null;
  loading: boolean;
  /** A turn is in flight. Guards double-clicks and auto-run loops. */
  generating: boolean;
  error: ApiError | null;
  /** True when the last failure is worth retrying with the same turn number. */
  canRetry: boolean;
  generateTurn: () => Promise<TurnResponse | null>;
  runAuto: () => Promise<void>;
  stopAuto: () => void;
  autoRunning: boolean;
  refresh: () => Promise<void>;
  applyBattle: (battle: BattleDetail) => void;
}

export function useBattle(battleId: string | undefined): BattleState {
  const [battle, setBattle] = useState<BattleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [canRetry, setCanRetry] = useState(false);
  const [autoRunning, setAutoRunning] = useState(false);

  const inFlight = useRef(false);
  const autoRef = useRef(false);
  const battleRef = useRef<BattleDetail | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const applyBattle = useCallback((next: BattleDetail) => {
    battleRef.current = next;
    setBattle(next);
  }, []);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      if (!battleId) return;
      setLoading(true);
      try {
        const detail = await fetchBattle(battleId, signal);
        applyBattle(detail);
        setError(null);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof ApiError ? err : new ApiError("Could not load this battle."));
      } finally {
        setLoading(false);
      }
    },
    [battleId, applyBattle],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const refresh = useCallback(async () => {
    await load();
  }, [load]);

  const generateTurn = useCallback(async (): Promise<TurnResponse | null> => {
    const current = battleRef.current;
    if (!battleId || !current || inFlight.current) return null;
    if (current.status !== "in_progress" && current.status !== "created") return null;

    inFlight.current = true;
    setGenerating(true);
    setError(null);
    setCanRetry(false);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const result = await takeTurn(battleId, current.next_turn_number, controller.signal);
      // Merge: the turn response carries the verse and the new battle counters.
      const merged: BattleDetail = {
        ...battleRef.current!,
        ...result.battle,
        result: null,
        verses: result.created
          ? [...battleRef.current!.verses, result.verse]
          : battleRef.current!.verses.map((verse) =>
              verse.id === result.verse.id ? result.verse : verse,
            ),
      };
      applyBattle({ ...merged, verses: dedupeVerses(merged.verses) });

      if (result.battle.status === "awaiting_vote") {
        // Pull the full record so the result payload is complete.
        void load();
      }
      return result;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return null;
      const apiError =
        err instanceof ApiError ? err : new ApiError("The turn could not be generated.");
      setError(apiError);
      setCanRetry(RETRYABLE_STATUS.has(apiError.code) || apiError.code === "NETWORK_ERROR");
      return null;
    } finally {
      inFlight.current = false;
      abortRef.current = null;
      setGenerating(false);
    }
  }, [battleId, applyBattle, load]);

  const stopAuto = useCallback(() => {
    autoRef.current = false;
    setAutoRunning(false);
    abortRef.current?.abort();
  }, []);

  const runAuto = useCallback(async () => {
    if (autoRef.current) return;
    autoRef.current = true;
    setAutoRunning(true);
    try {
      // Sequential, one turn at a time; stops on error, never double-fires.
      for (;;) {
        if (!autoRef.current) break;
        const current = battleRef.current;
        if (!current) break;
        if (current.status !== "in_progress" && current.status !== "created") break;
        if (current.next_turn_number > current.total_turns) break;
        const result = await generateTurn();
        if (!result) break;
      }
    } finally {
      autoRef.current = false;
      setAutoRunning(false);
    }
  }, [generateTurn]);

  useEffect(() => {
    return () => {
      autoRef.current = false;
      abortRef.current?.abort();
    };
  }, []);

  return {
    battle,
    loading,
    generating,
    error,
    canRetry,
    generateTurn,
    runAuto,
    stopAuto,
    autoRunning,
    refresh,
    applyBattle,
  };
}

function dedupeVerses<T extends { id: string; turn_number: number }>(verses: T[]): T[] {
  const byTurn = new Map<number, T>();
  for (const verse of verses) byTurn.set(verse.turn_number, verse);
  return [...byTurn.values()].sort((a, b) => a.turn_number - b.turn_number);
}