import type { AudioAsset } from "../types/api";
import { post, request } from "./client";

/** Ask the backend to synthesize (or return cached) audio for a verse. */
export const requestVerseAudio = (verseId: string, signal?: AbortSignal) =>
  post<AudioAsset>(`/verses/${verseId}/audio`, {}, signal);

/** Absolute-ish URL usable as an <audio src>. Relative paths stay same-origin. */
export function audioUrl(asset: AudioAsset | null | undefined): string | null {
  if (!asset || asset.status !== "ready") return null;
  return asset.url;
}

export interface PreviewOptions {
  voiceId: string;
  text: string;
}

export async function previewVoice({ voiceId, text }: PreviewOptions): Promise<Blob> {
  const response = await fetch("/api/tts/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ voice_id: voiceId, text }),
  });
  if (!response.ok) {
    throw new Error("Voice preview failed.");
  }
  return response.blob();
}

export { request };
