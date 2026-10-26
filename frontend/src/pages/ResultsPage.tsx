import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { paletteFor, RobotAvatar, variantForName } from "../components/character/RobotAvatar";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingBlock } from "../components/ui/LoadingBlock";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { ApiError } from "../services/client";
import { fetchBattle, fetchResult, requestRematch } from "../services/battles";
import type { BattleDetail, Result } from "../types/api";

export function ResultsPage() {
  const { battleId } = useParams<{ battleId: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<Result | null>(null);
  const [battle, setBattle] = useState<BattleDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [rematching, setRematching] = useState(false);

  useDocumentTitle("Result");

  useEffect(() => {
    if (!battleId) return;
    const controller = new AbortController();
    setLoading(true);
    Promise.all([
      fetchResult(battleId, controller.signal),
      fetchBattle(battleId, controller.signal),
    ])
      .then(([resultData, battleData]) => {
        setResult(resultData);
        setBattle(battleData);
        setError(null);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof ApiError ? err.message : "Could not load the result.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [battleId]);

  async function handleRematch() {
    if (!battleId) return;
    setRematching(true);
    try {
      const next = await requestRematch(battleId);
      navigate(`/battle/${next.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The rematch could not be started.");
    } finally {
      setRematching(false);
    }
  }

  if (loading) {
    return (
      <AppShell narrow>
        <LoadingBlock label="Counting the votes…" />
      </AppShell>
    );
  }

  if (!result || !battle) {
    return (
      <AppShell narrow>
        <ErrorState message={error ?? "This battle could not be found."} />
      </AppShell>
    );
  }

  const winner = result.winner;
  const winnerCharacter = winner
    ? [battle.fighter_a, battle.fighter_b].find((fighter) => fighter.id === winner.character_id) ?? null
    : null;
  const totalVotes = result.vote_count;

  return (
    <AppShell narrow>
      <PageHeader
        title={result.is_draw ? "It's a draw!" : winner ? `${winner.name} wins!` : "Battle result"}
        subtitle={battle ? `Topic: ${battle.topic}` : undefined}
      />

      {!result.is_draw && winnerCharacter ? (
        <div
          className="bv-card flex flex-col items-center gap-2 px-6 py-8 text-center"
          style={{ borderColor: paletteFor(winnerCharacter.accent).body }}
        >
          <RobotAvatar
            accent={winnerCharacter.accent}
            variant={variantForName(winnerCharacter.name)}
            size={110}
            speaking
            label={`${winnerCharacter.name}, winner`}
          />
          <h2 className="text-2xl font-extrabold">{winnerCharacter.name}</h2>
          <p className="text-sm text-[var(--color-muted)]">{winnerCharacter.tagline}</p>
        </div>
      ) : (
        /* Unreachable today: a battle only reaches "completed" via cast_vote,
           which always sets a winner. Kept so a future draw rule renders safely. */
        <div className="bv-card px-6 py-8 text-center">
          <p className="text-lg font-bold">Nobody won this one.</p>
          <p className="text-sm text-[var(--color-muted)]">
            The votes tied, so both robots keep their dignity.
          </p>
        </div>
      )}

      <section aria-label="Vote tally" className="bv-card mt-4 px-5 py-4">
        <h2 className="text-sm font-bold uppercase tracking-wide text-[var(--color-muted)]">
          Votes ({totalVotes})
        </h2>
        <div className="mt-3 grid gap-3">
          {result.fighters.map((fighter) => {
            const palette = paletteFor(fighter.accent);
            const share = Math.round(fighter.vote_share * 100);
            return (
              <div key={fighter.character_id}>
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold">{fighter.name}</span>
                  <span className="text-[var(--color-muted)]">
                    {fighter.votes} {fighter.votes === 1 ? "vote" : "votes"} · {share}%
                  </span>
                </div>
                <div
                  className="mt-1 h-3 w-full overflow-hidden rounded-full bg-[#f5f1ec]"
                  role="img"
                  aria-label={`${fighter.name}: ${share} percent`}
                >
                  <div
                    className="h-full rounded-full transition-[width] duration-300"
                    style={{ width: `${share}%`, backgroundColor: palette.body }}
                  />
                </div>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-[var(--color-muted)]">
          Human vote only. No AI judge was used.
        </p>
      </section>

      {result.best_verse ? (
        <section aria-label="Best verse" className="bv-card mt-4 px-5 py-4">
          <h2 className="text-sm font-bold uppercase tracking-wide text-[var(--color-muted)]">
            Highlight line
          </h2>
          <blockquote className="mt-2 whitespace-pre-line border-l-4 pl-3 text-[1.02rem] leading-relaxed" style={{ borderColor: paletteFor(result.best_verse.accent).body }}>
            {result.best_verse.verse_text}
          </blockquote>
          <p className="mt-2 text-xs text-[var(--color-muted)]">
            {result.best_verse.character_name}
            {result.best_verse.is_demo ? " · demo line (scripted, not AI-generated)" : ""}
          </p>
        </section>
      ) : null}

      {error ? (
        <Banner tone="danger" role="alert" className="mt-4">
          {error}
        </Banner>
      ) : null}

      <div className="mt-5 flex flex-wrap gap-2">
        <Button variant="primary" onClick={() => void handleRematch()} busy={rematching}>
          Rematch
        </Button>
        <Button variant="secondary" onClick={() => navigate(`/battle/${battle.id}`)}>
          View transcript
        </Button>
        <Link
          to="/history"
          className="inline-flex min-h-[44px] items-center rounded-full px-4 text-sm font-semibold text-[var(--color-primary-ink)] no-underline hover:underline"
        >
          All battles
        </Link>
      </div>
    </AppShell>
  );
}