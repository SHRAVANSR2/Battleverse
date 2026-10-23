import { useCallback } from "react";

const KEY = "battleverse.voterKey";

/** Anonymous per-browser identity used to prevent double voting. */
export function useVoterKey(): string {
  const get = useCallback((): string => {
    try {
      const existing = window.localStorage.getItem(KEY);
      if (existing && /^[A-Za-z0-9_-]{8,64}$/.test(existing)) return existing;
      const generated = crypto.randomUUID().replace(/-/g, "");
      window.localStorage.setItem(KEY, generated);
      return generated;
    } catch {
      // Storage may be blocked; fall back to an in-memory key for this page load.
      return `anon${Math.random().toString(36).slice(2, 12)}`;
    }
  }, []);

  return get();
}