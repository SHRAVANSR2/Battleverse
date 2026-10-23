import type {
  BattleDetail,
  BattleSummary,
  Character,
  LeaderboardRow,
  Result,
  TurnResponse,
} from "../types/api";
import { get, post } from "./client";

export interface CreateBattleInput {
  fighter_a_id: string;
  fighter_b_id: string;
  topic: string;
  style: string;
  intensity: string;
  round_count: number;
  playback_mode: string;
}

export const fetchCharacters = (signal?: AbortSignal) =>
  get<Character[]>("/characters", signal);

export const createBattle = (input: CreateBattleInput) =>
  post<BattleDetail>("/battles", input);

export const fetchBattle = (battleId: string, signal?: AbortSignal) =>
  get<BattleDetail>(`/battles/${battleId}`, signal);

export const fetchBattles = (params: { status?: string; limit?: number } = {}, signal?: AbortSignal) => {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return get<BattleSummary[]>(`/battles${suffix}`, signal);
};

export const takeTurn = (
  battleId: string,
  expectedTurnNumber: number,
  signal?: AbortSignal,
) =>
  post<TurnResponse>(
    `/battles/${battleId}/turn`,
    { expected_turn_number: expectedTurnNumber },
    signal,
  );

export const fetchHistory = (signal?: AbortSignal) =>
  get<BattleSummary[]>("/history", signal);

export const fetchLeaderboard = (signal?: AbortSignal) =>
  get<LeaderboardRow[]>("/leaderboard", signal);

export const fetchResult = (battleId: string, signal?: AbortSignal) =>
  get<Result>(`/battles/${battleId}/result`, signal);

export const castVote = (battleId: string, winnerId: string, voterKey: string) =>
  post<{ vote: unknown; battle: BattleDetail; result: Result }>(
    `/battles/${battleId}/vote`,
    { winner_character_id: winnerId, voter_key: voterKey },
  );

export const requestRematch = (battleId: string) =>
  post<BattleDetail>(`/battles/${battleId}/rematch`, {});
