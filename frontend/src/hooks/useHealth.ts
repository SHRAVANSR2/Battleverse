import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../services/client";
import { fetchHealth } from "../services/system";
import type { Health } from "../types/api";

export interface HealthState {
  health: Health | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/** Live backend status: used by the nav pill and the home page footer. */
export function useHealth(): HealthState {
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const refresh = useCallback(() => setNonce((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);

    fetchHealth(controller.signal)
      .then((data) => {
        if (!active) return;
        setHealth(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!active || (err instanceof DOMException && err.name === "AbortError")) return;
        setError(err instanceof ApiError ? err.message : "Cannot reach the backend.");
        setHealth(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [nonce]);

  return { health, loading, error, refresh };
}