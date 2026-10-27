import { describe, expect, it } from "vitest";
import {
  audioReducer,
  initialAudioState,
  pickNext,
  type AudioState,
} from "./audioMachine";

function withQueue(ids: string[], src = "/api/audio/x"): AudioState {
  return audioReducer(initialAudioState, {
    type: "REPLACE_QUEUE",
    items: ids.map((verseId) => ({ verseId, src })),
  });
}

describe("audioMachine", () => {
  it("enqueues without duplicating an existing verse", () => {
    const state = audioReducer(initialAudioState, {
      type: "ENQUEUE",
      items: [{ verseId: "a" }, { verseId: "b" }],
    });
    const again = audioReducer(state, {
      type: "ENQUEUE",
      items: [{ verseId: "a" }, { verseId: "c" }],
    });
    expect(again.queue.map((item) => item.verseId)).toEqual(["a", "b", "c"]);
  });

  it("play switches the active verse and only one item is active", () => {
    let state = withQueue(["a", "b"]);
    state = audioReducer(state, { type: "PLAY", verseId: "a" });
    state = audioReducer(state, { type: "PLAYING", verseId: "a" });
    state = audioReducer(state, { type: "PLAY", verseId: "b" });

    expect(state.activeVerseId).toBe("b");
    expect(state.queue.find((i) => i.verseId === "b")?.state).toBe("loading");
    expect(state.queue.find((i) => i.verseId === "a")?.state).toBe("ready");
  });

  it("never reports speaking until the element emits a real playing event", () => {
    let state = withQueue(["a"]);
    state = audioReducer(state, { type: "PLAY", verseId: "a" });
    // A click only starts loading; the highlight must stay off.
    expect(state.mode).toBe("generating");
    expect(state.activeVerseId).toBe("a");

    state = audioReducer(state, { type: "PLAYING", verseId: "a" });
    expect(state.mode).toBe("playing");

    state = audioReducer(state, { type: "PAUSED", verseId: "a" });
    expect(state.mode).not.toBe("playing");
  });

  it("does not advance while paused", () => {
    let state = withQueue(["a", "b"]);
    state = audioReducer(state, { type: "PLAY", verseId: "a" });
    state = audioReducer(state, { type: "PLAYING", verseId: "a" });
    state = audioReducer(state, { type: "PAUSED", verseId: "a" });
    expect(state.mode).toBe("paused");
    expect(state.activeVerseId).toBe("a");
  });

  it("picks the next playable item after the active one", () => {
    let state = withQueue(["a", "b", "c"]);
    state = audioReducer(state, { type: "PLAY", verseId: "a" });
    state = audioReducer(state, { type: "PLAYING", verseId: "a" });
    expect(pickNext(state)?.verseId).toBe("b");
  });

  it("skips failed items when choosing the next one", () => {
    let state = withQueue(["a", "b", "c"]);
    state = audioReducer(state, { type: "PLAYING", verseId: "a" });
    state = audioReducer(state, { type: "FAILED", verseId: "b", message: "nope" });
    expect(pickNext(state)?.verseId).toBe("c");
  });

  it("does not autoplay when the toggle is off", () => {
    let state = withQueue(["a", "b"]);
    state = audioReducer(state, { type: "SET_AUTOPLAY", autoplay: false });
    state = audioReducer(state, { type: "PLAYING", verseId: "a" });
    expect(pickNext(state)).toBeNull();
  });

  it("STOP_ALL clears activity and requeues in-flight items", () => {
    let state = withQueue(["a", "b"]);
    state = audioReducer(state, { type: "PLAY", verseId: "a" });
    state = audioReducer(state, { type: "PLAYING", verseId: "a" });
    state = audioReducer(state, { type: "STOP_ALL" });
    expect(state.mode).toBe("idle");
    expect(state.activeVerseId).toBeNull();
    expect(state.queue.every((item) => item.state === "ready")).toBe(true);
  });

  it("replay-style ENDED leaves state idle without auto-advance by itself", () => {
    let state = withQueue(["a"]);
    state = audioReducer(state, { type: "PLAYING", verseId: "a" });
    state = audioReducer(state, { type: "ENDED", verseId: "a" });
    expect(state.mode).toBe("idle");
    expect(state.queue[0]?.state).toBe("ready");
  });

  it("clamps volume", () => {
    let state = audioReducer(initialAudioState, { type: "SET_VOLUME", volume: 5 });
    expect(state.volume).toBe(1);
    state = audioReducer(state, { type: "SET_VOLUME", volume: -2 });
    expect(state.volume).toBe(0);
  });

  it("records the blocked reason", () => {
    const state = audioReducer(initialAudioState, {
      type: "BLOCKED",
      reason: "Tap play.",
    });
    expect(state.mode).toBe("blocked");
    expect(state.blockedReason).toBe("Tap play.");
  });

  it("syncing the queue with new verses never disturbs the one being spoken", () => {
    let state = withQueue(["v1", "v2"], "");
    state = audioReducer(state, { type: "PLAY", verseId: "v1" });
    state = audioReducer(state, { type: "SET_SRC", verseId: "v1", src: "/api/audio/v1" });
    state = audioReducer(state, { type: "PLAYING", verseId: "v1" });

    // auto mode: two more verses land while v1 is still speaking
    state = audioReducer(state, {
      type: "REPLACE_QUEUE",
      items: ["v1", "v2", "v3", "v4"].map((verseId) => ({ verseId, src: null })),
    });

    expect(state.activeVerseId).toBe("v1");
    expect(state.mode).toBe("playing");
    expect(state.queue.find((i) => i.verseId === "v1")?.src).toBe("/api/audio/v1");
    expect(state.queue.map((i) => i.verseId)).toEqual(["v1", "v2", "v3", "v4"]);
    expect(state.queue.find((i) => i.verseId === "v4")?.state).toBe("queued");
  });

  it("never restarts from the top when nothing is active", () => {
    let state = withQueue(["v1", "v2"], "");
    state = audioReducer(state, { type: "ADVANCE" });
    expect(state.activeVerseId).toBeNull();
    expect(state.mode).toBe("idle");
  });

  it("remembers that the listener pressed Stop until they press Play", () => {
    let state = withQueue(["v1", "v2"], "");
    state = audioReducer(state, { type: "PLAY", verseId: "v1" });
    state = audioReducer(state, { type: "STOP_ALL" });
    expect(state.stoppedByUser).toBe(true);
    state = audioReducer(state, { type: "PLAY", verseId: "v2" });
    expect(state.stoppedByUser).toBe(false);
  });
});