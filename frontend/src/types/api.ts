/** Wire types mirroring the FastAPI schemas. */

export type BattleStyle = "rap" | "roast" | "debate";
export type Intensity = "playful" | "spicy" | "fiery";
export type PlaybackMode = "manual" | "auto";
export type BattleStatus =
  | "created"
  | "in_progress"
  | "awaiting_vote"
  | "completed"
  | "failed";
export type AudioStatus = "pending" | "ready" | "failed";

export interface ApiErrorBody {
  code: string;
  message: string;
  request_id: string;
  details?: { fields?: { field: string; message: string }[] } | Record<string, unknown>;
}

export interface Health {
  status: string;
  version: string;
  database_ready: boolean;
  llm_provider: "groq" | "demo";
  llm_model: string;
  llm_key_present: boolean;
  demo_mode: boolean;
  tts_provider: "piper" | "fake";
  tts_voices: number;
  tts_ready: boolean;
}

export interface Character {
  id: string;
  slug: string;
  name: string;
  tagline: string;
  description: string;
  personality: Record<string, unknown>;
  style_pref: string;
  catchphrase: string;
  voice_id: string;
  accent: "mint" | "coral" | string;
  is_builtin: boolean;
  sort_order: number;
  created_at: string;
}

export interface AudioAsset {
  id: string;
  verse_id: string;
  provider: string;
  voice_id: string;
  url: string;
  content_type: string;
  size_bytes: number;
  duration_ms: number;
  status: AudioStatus;
  error_code?: string | null;
  cached?: boolean;
}

export interface Verse {
  id: string;
  battle_id: string;
  character_id: string;
  character_name: string;
  accent: string;
  round_number: number;
  turn_number: number;
  verse_text: string;
  line_count: number;
  model: string;
  provider: "groq" | "demo" | string;
  is_demo: boolean;
  created_at: string;
  audio?: AudioAsset | null;
}

export interface Battle {
  id: string;
  topic: string;
  style: BattleStyle;
  intensity: Intensity;
  round_count: number;
  playback_mode: PlaybackMode;
  status: BattleStatus;
  current_round: number;
  next_turn_number: number;
  total_turns: number;
  state_version: number;
  previous_battle_id?: string | null;
  winner_character_id?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface FighterResult {
  character_id: string;
  name: string;
  accent: string;
  votes: number;
  vote_share: number;
}

export interface Result {
  battle_id: string;
  status: BattleStatus;
  is_draw: boolean;
  winner: FighterResult | null;
  fighters: FighterResult[];
  vote_count: number;
  best_verse: Verse | null;
  ai_judge: null;
  decided_at?: string | null;
}

export interface BattleDetail extends Battle {
  fighter_a: Character;
  fighter_b: Character;
  verses: Verse[];
  result?: Result | null;
}

export interface BattleSummary extends Battle {
  fighter_a_name: string;
  fighter_b_name: string;
  fighter_a_accent: string;
  fighter_b_accent: string;
  fighter_a_slug: string;
  fighter_b_slug: string;
  verse_count: number;
  winner_name?: string | null;
  rival_note?: string | null;
}

export interface TurnResponse {
  battle: Battle;
  verse: Verse;
  created: boolean;
}

export interface LeaderboardRow {
  character_id: string;
  slug: string;
  name: string;
  accent: string;
  battles: number;
  wins: number;
  losses: number;
  win_rate: number;
  last_battle_at?: string | null;
}