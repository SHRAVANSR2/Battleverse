/**
 * Regression test for auto mode: robot A speaks, robot B must follow
 * automatically even though B's audio did not exist yet and more verses were
 * generated while A was talking.
 */
import { act, render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Verse } from "../types/api";
import { AudioProvider, useAudio } from "./AudioProvider";

const requestVerseAudio = vi.fn();
vi.mock("../services/audio", () => ({
  requestVerseAudio: (...args: unknown[]) => requestVerseAudio(...args),
}));

class FakeAudio {
  static last: FakeAudio;
  src = "";
  muted = false;
  volume = 1;
  ended = false;
  preload = "";
  private listeners = new Map<string, Set<() => void>>();
  constructor() {
    FakeAudio.last = this;
  }
  addEventListener(type: string, fn: () => void) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(fn);
  }
  removeEventListener(type: string, fn: () => void) {
    this.listeners.get(type)?.delete(fn);
  }
  emit(type: string) {
    this.listeners.get(type)?.forEach((fn) => fn());
  }
  load() {}
  pause() {}
  removeAttribute() {
    this.src = "";
  }
  play() {
    queueMicrotask(() => this.emit("playing"));
    return Promise.resolve();
  }
}

const verse = (id: string): Verse => ({ id, audio: null }) as unknown as Verse;

let api: ReturnType<typeof useAudio>;
function Probe() {
  api = useAudio();
  return null;
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe("AudioProvider auto hand-off", () => {
  beforeEach(() => {
    requestVerseAudio.mockReset();
    requestVerseAudio.mockImplementation(async (id: string) => ({ url: `/api/audio/${id}` }));
    vi.stubGlobal("Audio", FakeAudio);
  });

  it("speaks the next robot automatically, even when new verses arrive mid-speech", async () => {
    render(
      <AudioProvider>
        <Probe />
      </AudioProvider>,
    );

    act(() => api.queueVerses([verse("v1"), verse("v2")]));
    await act(async () => {
      await api.playVerse("v1");
    });
    await flush();
    expect(api.isSpeaking("v1")).toBe(true);

    // more turns are generated while v1 is still talking
    act(() => api.queueVerses([verse("v1"), verse("v2"), verse("v3"), verse("v4")]));
    await flush();
    expect(api.isSpeaking("v1")).toBe(true); // untouched

    // v1 finishes -> v2 (no audio yet) must be fetched and spoken
    await act(async () => {
      FakeAudio.last.ended = true;
      FakeAudio.last.emit("ended");
    });
    await flush();
    await flush();

    expect(requestVerseAudio).toHaveBeenCalledWith("v2", expect.anything());
    expect(api.isSpeaking("v2")).toBe(true);
    expect(api.pendingFor("v2")).toBe(false);
  });

  it("does not restart anything after the listener presses Stop", async () => {
    render(
      <AudioProvider>
        <Probe />
      </AudioProvider>,
    );
    act(() => api.queueVerses([verse("v1"), verse("v2")]));
    await act(async () => {
      await api.playVerse("v1");
    });
    await flush();

    act(() => api.stop());
    await flush();

    expect(api.state.activeVerseId).toBeNull();
    expect(api.state.stoppedByUser).toBe(true);
    expect(requestVerseAudio).toHaveBeenCalledTimes(1); // v2 was never fetched
  });
});