import type { BattleDetail, Character, Verse } from "../types/api";

export const nova: Character = {
  id: "char-nova",
  slug: "nova-vex",
  name: "Nova Vex",
  tagline: "Sparkly chaos, undefeated at puns.",
  description: "A chirpy show-off robot.",
  personality: {},
  style_pref: "rap",
  catchphrase: "Light it up, buttercup!",
  voice_id: "en_US-kristin-medium",
  accent: "mint",
  is_builtin: true,
  sort_order: 1,
  created_at: "2026-10-23T10:00:00Z",
};

export const rook: Character = {
  ...nova,
  id: "char-rook",
  slug: "rook-blaze",
  name: "Rook Blaze",
  tagline: "Warm heart, colder delivery.",
  voice_id: "en_US-joe-medium",
  accent: "coral",
  sort_order: 2,
};

export function makeVerse(overrides: Partial<Verse> = {}): Verse {
  return {
    id: "verse-1",
    battle_id: "battle-1",
    character_id: nova.id,
    character_name: nova.name,
    accent: nova.accent,
    round_number: 1,
    turn_number: 1,
    verse_text: "First line about antennas\nSecond line about chrome",
    line_count: 2,
    model: "scripted-demo-writer",
    provider: "demo",
    is_demo: true,
    created_at: "2026-10-23T10:00:00Z",
    audio: null,
    ...overrides,
  };
}

export function makeBattle(overrides: Partial<BattleDetail> = {}): BattleDetail {
  return {
    id: "battle-1",
    topic: "best antenna polish",
    style: "rap",
    intensity: "playful",
    round_count: 1,
    playback_mode: "manual",
    status: "in_progress",
    current_round: 0,
    next_turn_number: 1,
    total_turns: 2,
    state_version: 0,
    previous_battle_id: null,
    winner_character_id: null,
    created_at: "2026-10-23T10:00:00Z",
    completed_at: null,
    fighter_a: nova,
    fighter_b: rook,
    verses: [],
    result: null,
    ...overrides,
  };
}