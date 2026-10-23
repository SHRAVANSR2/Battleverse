import { useEffect, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { paletteFor, RobotAvatar, variantForName } from "../components/character/RobotAvatar";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingBlock } from "../components/ui/LoadingBlock";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { ApiError } from "../services/client";
import { fetchLeaderboard } from "../services/battles";
import type { LeaderboardRow } from "../types/api";

export function LeaderboardPage() {
  useDocumentTitle("Leaderboard");
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetchLeaderboard(controller.signal)
      .then((data) => {
        setRows(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof ApiError ? err.message : "Could not load the leaderboard.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [nonce]);

  return (
    <AppShell narrow>
      <PageHeader title="Leaderboard" subtitle="Head-to-head record of the built-in robots." />

      {loading ? <LoadingBlock /> : null}
      {error ? <ErrorState message={error} onRetry={() => setNonce((n) => n + 1)} /> : null}

      {!loading && !error ? (
        rows.every((row) => row.battles === 0) ? (
          <EmptyState title="No winners yet">Finish a battle to start the rankings.</EmptyState>
        ) : (
          <ol className="grid gap-3">
            {rows.map((row, index) => {
              const palette = paletteFor(row.accent);
              return (
                <li key={row.character_id} className="bv-card flex items-center gap-3 px-4 py-3">
                  <span
                    className="grid size-8 shrink-0 place-items-center rounded-full text-sm font-extrabold"
                    style={{ backgroundColor: palette.glow, color: palette.dark }}
                    aria-label={`Rank ${index + 1}`}
                  >
                    {index + 1}
                  </span>
                  <RobotAvatar
                    accent={row.accent}
                    variant={variantForName(row.name)}
                    size={44}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="font-bold">{row.name}</p>
                    <p className="text-xs text-[var(--color-muted)]">
                      {row.wins} wins · {row.losses} losses · {row.battles} battles
                    </p>
                  </div>
                  <span className="text-lg font-extrabold" style={{ color: palette.dark }}>
                    {Math.round(row.win_rate * 100)}%
                  </span>
                </li>
              );
            })}
          </ol>
        )
      ) : null}
    </AppShell>
  );
}