import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { RobotAvatar, variantForName } from "../components/character/RobotAvatar";
import { Button } from "../components/ui/Button";
import { Chip } from "../components/ui/Chip";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingBlock } from "../components/ui/LoadingBlock";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { ApiError } from "../services/client";
import { fetchHistory, requestRematch } from "../services/battles";
import type { BattleSummary } from "../types/api";

export function HistoryPage() {
  useDocumentTitle("History");
  const navigate = useNavigate();
  const [battles, setBattles] = useState<BattleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [nonce, setNonce] = useState(0);
  const [rematchingId, setRematchingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetchHistory(controller.signal)
      .then((data) => {
        setBattles(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof ApiError ? err : new ApiError("Could not load history."));
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [nonce]);

  const reload = useMemo(() => () => setNonce((value) => value + 1), []);

  async function rematch(battle: BattleSummary) {
    setRematchingId(battle.id);
    try {
      const next = await requestRematch(battle.id);
      navigate(`/battle/${next.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError("The rematch could not be started."));
    } finally {
      setRematchingId(null);
    }
  }

  return (
    <AppShell narrow>
      <PageHeader
        title="Battle history"
        subtitle="Every finished battle, newest first. Rivalries carry over into rematches."
      />

      {loading ? <LoadingBlock label="Fetching battles…" /> : null}

      {error && !loading ? <ErrorState message={error.message} code={error.code} onRetry={reload} /> : null}

      {!loading && !error && battles.length === 0 ? (
        <EmptyState
          title="No battles yet"
          action={
            <Link
              to="/battle/new"
              className="mt-1 inline-flex min-h-[44px] items-center rounded-full bg-[var(--color-primary)] px-5 font-semibold text-white no-underline"
            >
              Start the first battle
            </Link>
          }
        >
          Two robots are waiting and the mic is free.
        </EmptyState>
      ) : null}

      {!loading && battles.length > 0 ? (
        <ul className="grid gap-3">
          {battles.map((battle) => (
            <li key={battle.id} className="bv-card flex flex-wrap items-center gap-3 px-4 py-3">
              <div className="flex items-center gap-2">
                <RobotAvatar
                  accent={battle.fighter_a_accent}
                  variant={variantForName(battle.fighter_a_name)}
                  size={40}
                />
                <span className="text-xs font-bold text-[var(--color-muted)]">vs</span>
                <RobotAvatar
                  accent={battle.fighter_b_accent}
                  variant={variantForName(battle.fighter_b_name)}
                  size={40}
                />
              </div>

              <div className="min-w-[12rem] flex-1">
                <p className="text-sm font-bold">
                  {battle.fighter_a_name} vs {battle.fighter_b_name}
                </p>
                <p className="truncate text-xs text-[var(--color-muted)]">Topic: {battle.topic}</p>
                {battle.rival_note ? (
                  <p className="mt-0.5 text-xs font-semibold" style={{ color: "var(--color-primary-ink)" }}>
                    {battle.rival_note}
                  </p>
                ) : null}
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                <Chip tone="neutral">{battle.round_count} rounds</Chip>
                {battle.status === "completed" && battle.winner_name ? (
                  <Chip tone="ok">Won by {battle.winner_name}</Chip>
                ) : battle.status === "awaiting_vote" ? (
                  <Chip tone="warn">Awaiting vote</Chip>
                ) : (
                  <Chip tone="neutral">In progress</Chip>
                )}
                {battle.verse_count > 0 ? (
                  <Chip tone="neutral">{battle.verse_count} verses</Chip>
                ) : null}
              </div>

              <div className="flex gap-2">
                <Button size="sm" variant="secondary" onClick={() => navigate(`/battle/${battle.id}`)}>
                  Open
                </Button>
                {battle.status !== "in_progress" ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => void rematch(battle)}
                    busy={rematchingId === battle.id}
                  >
                    Rematch
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </AppShell>
  );
}