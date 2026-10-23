import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { BattleDetail } from "../../types/api";
import { ApiError } from "../../services/client";
import { castVote } from "../../services/battles";
import { useVoterKey } from "../../hooks/useVoterKey";
import { paletteFor, RobotAvatar, variantForName } from "../character/RobotAvatar";
import { Banner } from "../ui/Banner";
import { Button } from "../ui/Button";

export interface VotingPanelProps {
  battle: BattleDetail;
  onDecided: () => void;
}

export function VotingPanel({ battle, onDecided }: VotingPanelProps) {
  const voterKey = useVoterKey();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [voteErrorCode, setVoteErrorCode] = useState<string | null>(null);

  const open = battle.status === "awaiting_vote";

  async function vote(characterId: string) {
    setBusy(characterId);
    setError(null);
    setVoteErrorCode(null);
    try {
      await castVote(battle.id, characterId, voterKey);
      onDecided();
      navigate(`/battle/${battle.id}/result`);
    } catch (err) {
      const apiError = err instanceof ApiError ? err : null;
      setError(apiError?.message ?? "Your vote could not be recorded.");
      setVoteErrorCode(apiError?.code ?? null);
      if (apiError?.code === "ALREADY_VOTED") {
        onDecided();
      }
    } finally {
      setBusy(null);
    }
  }

  if (!open) {
    return (
      <div className="bv-card flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <p className="text-sm text-[var(--color-muted)]">
          This battle is decided. The full result page has the tally.
        </p>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => navigate(`/battle/${battle.id}/result`)}>
            View result
          </Button>
        </div>
      </div>
    );
  }

  return (
    <section aria-label="Vote for a winner" className="bv-card px-5 py-4">
      <h2 className="text-lg font-bold">Who won?</h2>
      <p className="mt-1 text-sm text-[var(--color-muted)]">
        Human votes only — no AI judge. Pick the robot whose lines landed best.
      </p>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {[battle.fighter_a, battle.fighter_b].map((fighter, index) => {
          const palette = paletteFor(fighter.accent);
          return (
            <button
              key={fighter.id}
              type="button"
              onClick={() => void vote(fighter.id)}
              disabled={busy !== null}
              className="bv-transition flex min-h-[64px] items-center gap-3 rounded-2xl border-2 px-4 py-3 text-left font-semibold hover:bg-white disabled:opacity-60"
              style={{ borderColor: palette.body }}
              aria-label={`Vote for ${fighter.name}`}
            >
              <RobotAvatar
                accent={fighter.accent}
                variant={variantForName(fighter.name)}
                size={44}
              />
              <span>
                Vote for {fighter.name}
                <span className="block text-xs font-normal text-[var(--color-muted)]">
                  Robot {index === 0 ? "A" : "B"}
                </span>
              </span>
              {busy === fighter.id ? (
                <span className="ml-auto text-xs text-[var(--color-muted)]">Saving…</span>
              ) : null}
            </button>
          );
        })}
      </div>

      {error ? (
        <Banner tone="danger" role="alert" className="mt-3">
          {error}
          {voteErrorCode === "ALREADY_VOTED" ? (
            <span className="block text-xs opacity-80">
              One vote per browser per battle. The result page has the tally.
            </span>
          ) : null}
        </Banner>
      ) : null}
    </section>
  );
}