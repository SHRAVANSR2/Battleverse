import type { Health, VoiceInfo } from "../types/api";
import { get } from "./client";

export const fetchHealth = (signal?: AbortSignal) => get<Health>("/health", signal);

export const fetchVoices = (signal?: AbortSignal) =>
  get<VoiceInfo[]>("/tts/voices", signal);