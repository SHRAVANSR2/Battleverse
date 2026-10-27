/**
 * Tiny procedural boom-bap beat for rap battles. No audio files: every drum hit
 * and bass note is synthesised with the Web Audio API.
 *
 * One engine, three profiles over the same 16-step scheduler:
 *   rap    – 90 BPM boom-bap: kick 0/6/10, snare 4/12, swung 8th hats,
 *            808 A-A-F-G, Am stab on bars 1 and 3
 *   roast  – 72 BPM: kick 0/8, snare 4/12, no hats, no stabs (lazier, meaner)
 *   debate – 60 BPM: kick 0, soft "gavel" thump on 8, sparse hat on 4/12,
 *            no bass, no stabs (a ticking-clock feel)
 */

export type BeatProfile = "rap" | "roast" | "debate";

const STEPS_PER_BAR = 16;
const LOOP_BARS = 4;
const LOOKAHEAD_SECONDS = 0.14;
const TICK_MS = 30;

const PROFILES: Record<BeatProfile, { bpm: number }> = {
  rap: { bpm: 90 },
  roast: { bpm: 72 },
  debate: { bpm: 60 },
};

function stepSeconds(bpm: number): number {
  return 60 / bpm / 4;
}

const BASS_NOTES = [55, 55, 43.65, 49]; // A1, A1, F1, G1
const CHORD = [220, 261.63, 329.63]; // Am

type AudioContextCtor = typeof AudioContext;

function contextCtor(): AudioContextCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { AudioContext?: AudioContextCtor; webkitAudioContext?: AudioContextCtor };
  return w.AudioContext ?? w.webkitAudioContext ?? null;
}

export function beatSupported(): boolean {
  return contextCtor() !== null;
}

export class BeatEngine {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private noise: AudioBuffer | null = null;
  private timer: number | null = null;
  private stopTimer: number | null = null;
  private nextTime = 0;
  private step = 0;
  private profile: BeatProfile = "rap";
  private stepSeconds = stepSeconds(PROFILES.rap.bpm);

  get running(): boolean {
    return this.timer !== null;
  }

  /** Start (or keep) the loop. Safe to call repeatedly. */
  start(level: number, profile: BeatProfile = "rap"): void {
    if (profile !== this.profile) {
      // A profile change mid-battle (rematch into a new style) restarts the
      // scheduler so the new tempo takes effect immediately.
      this.stopNow();
      this.profile = profile;
      this.stepSeconds = stepSeconds(PROFILES[profile].bpm);
      this.step = 0;
    }
    if (this.stopTimer !== null) {
      window.clearTimeout(this.stopTimer);
      this.stopTimer = null;
    }
    const Ctor = contextCtor();
    if (!Ctor) return;
    if (!this.ctx) {
      this.ctx = new Ctor();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0;
      this.master.connect(this.ctx.destination);
      this.noise = this.makeNoise(this.ctx);
    }
    void this.ctx.resume();
    this.fadeTo(level, 0.25);
    if (this.timer !== null) return;
    this.nextTime = this.ctx.currentTime + 0.06;
    this.timer = window.setInterval(this.tick, TICK_MS);
  }

  /** Hard-stop the scheduler with no fade-out (used before a profile switch). */
  private stopNow(): void {
    if (this.timer !== null) window.clearInterval(this.timer);
    if (this.stopTimer !== null) window.clearTimeout(this.stopTimer);
    this.timer = null;
    this.stopTimer = null;
  }

  setLevel(level: number): void {
    if (this.running) this.fadeTo(level, 0.1);
  }

  /** Fade out, then halt the scheduler. */
  stop(): void {
    if (this.timer === null) return;
    this.fadeTo(0, 0.3);
    if (this.stopTimer !== null) window.clearTimeout(this.stopTimer);
    this.stopTimer = window.setTimeout(() => {
      if (this.timer !== null) window.clearInterval(this.timer);
      this.timer = null;
      this.stopTimer = null;
    }, 700);
  }

  dispose(): void {
    if (this.timer !== null) window.clearInterval(this.timer);
    if (this.stopTimer !== null) window.clearTimeout(this.stopTimer);
    this.timer = null;
    this.stopTimer = null;
    void this.ctx?.close();
    this.ctx = null;
    this.master = null;
  }

  // ---------------------------------------------------------------- internals

  private fadeTo(value: number, seconds: number): void {
    if (!this.ctx || !this.master) return;
    this.master.gain.setTargetAtTime(value, this.ctx.currentTime, seconds / 3);
  }

  private makeNoise(ctx: AudioContext): AudioBuffer {
    const buffer = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i += 1) data[i] = Math.random() * 2 - 1;
    return buffer;
  }

  private tick = (): void => {
    const ctx = this.ctx;
    if (!ctx) return;
    while (this.nextTime < ctx.currentTime + LOOKAHEAD_SECONDS) {
      this.schedule(this.step, this.nextTime);
      this.nextTime += this.stepSeconds;
      this.step = (this.step + 1) % (STEPS_PER_BAR * LOOP_BARS);
    }
  };

  private schedule(stepInLoop: number, time: number): void {
    const bar = Math.floor(stepInLoop / STEPS_PER_BAR) % LOOP_BARS;
    const step = stepInLoop % STEPS_PER_BAR;
    const profile = this.profile;

    if (profile === "rap") {
      const swing = step % 4 === 2 ? 0.018 : 0; // lazy off-beat 8ths
      if (step === 0 || step === 6 || step === 10) this.kick(time, step === 0 ? 1 : 0.8);
      if (step === 4 || step === 12) this.snare(time);
      if (step % 2 === 0) this.hat(time + swing, step === 14 ? "open" : "closed", step % 4 === 0 ? 1 : 0.6);
      if (step === 0 || step === 10) this.bass(BASS_NOTES[bar]!, time, step === 0 ? 0.55 : 0.32);
      if (step === 8 && (bar === 0 || bar === 2)) this.stab(time);
      return;
    }
    if (profile === "roast") {
      if (step === 0 || step === 8) this.kick(time, step === 0 ? 1 : 0.75);
      if (step === 4 || step === 12) this.snare(time);
      if (step === 0) this.bass(BASS_NOTES[bar]!, time, 0.5);
      return;
    }
    // debate: a slow ticking clock
    if (step === 0) this.kick(time, 0.85);
    if (step === 8) this.thump(time);
    if (step === 4 || step === 12) this.hat(time, "closed", 0.35);
  }

  /** Low muted thump (debate's "gavel"), distinct from the snare. */
  private thump(time: number): void {
    const ctx = this.ctx!;
    const osc = ctx.createOscillator();
    const amp = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(90, time);
    osc.frequency.exponentialRampToValueAtTime(55, time + 0.09);
    amp.gain.setValueAtTime(0.4, time);
    amp.gain.exponentialRampToValueAtTime(0.001, time + 0.18);
    osc.connect(amp).connect(this.out());
    osc.start(time);
    osc.stop(time + 0.2);
  }

  private out(): GainNode {
    return this.master as GainNode;
  }

  private kick(time: number, gain: number): void {
    const ctx = this.ctx!;
    const osc = ctx.createOscillator();
    const amp = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(150, time);
    osc.frequency.exponentialRampToValueAtTime(42, time + 0.12);
    amp.gain.setValueAtTime(0.9 * gain, time);
    amp.gain.exponentialRampToValueAtTime(0.001, time + 0.35);
    osc.connect(amp).connect(this.out());
    osc.start(time);
    osc.stop(time + 0.4);
  }

  private snare(time: number): void {
    const ctx = this.ctx!;
    const src = ctx.createBufferSource();
    src.buffer = this.noise;
    const filter = ctx.createBiquadFilter();
    filter.type = "highpass";
    filter.frequency.value = 1400;
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0.5, time);
    amp.gain.exponentialRampToValueAtTime(0.001, time + 0.22);
    src.connect(filter).connect(amp).connect(this.out());
    src.start(time);
    src.stop(time + 0.25);

    const body = ctx.createOscillator();
    const bodyAmp = ctx.createGain();
    body.type = "triangle";
    body.frequency.setValueAtTime(190, time);
    body.frequency.exponentialRampToValueAtTime(110, time + 0.08);
    bodyAmp.gain.setValueAtTime(0.35, time);
    bodyAmp.gain.exponentialRampToValueAtTime(0.001, time + 0.12);
    body.connect(bodyAmp).connect(this.out());
    body.start(time);
    body.stop(time + 0.15);
  }

  private hat(time: number, kind: "closed" | "open", accent: number): void {
    const ctx = this.ctx!;
    const src = ctx.createBufferSource();
    src.buffer = this.noise;
    const filter = ctx.createBiquadFilter();
    filter.type = "highpass";
    filter.frequency.value = 7500;
    const amp = ctx.createGain();
    const length = kind === "open" ? 0.2 : 0.045;
    amp.gain.setValueAtTime(0.16 * accent, time);
    amp.gain.exponentialRampToValueAtTime(0.001, time + length);
    src.connect(filter).connect(amp).connect(this.out());
    src.start(time);
    src.stop(time + length + 0.02);
  }

  private bass(freq: number, time: number, gain: number): void {
    const ctx = this.ctx!;
    const osc = ctx.createOscillator();
    const amp = ctx.createGain();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(freq * 1.5, time);
    osc.frequency.exponentialRampToValueAtTime(freq, time + 0.05);
    amp.gain.setValueAtTime(0.0001, time);
    amp.gain.exponentialRampToValueAtTime(gain, time + 0.015);
    amp.gain.exponentialRampToValueAtTime(0.001, time + 0.55);
    osc.connect(amp).connect(this.out());
    osc.start(time);
    osc.stop(time + 0.6);
  }

  private stab(time: number): void {
    const ctx = this.ctx!;
    for (const freq of CHORD) {
      const osc = ctx.createOscillator();
      const amp = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.value = freq;
      amp.gain.setValueAtTime(0.0001, time);
      amp.gain.exponentialRampToValueAtTime(0.07, time + 0.01);
      amp.gain.exponentialRampToValueAtTime(0.001, time + 0.28);
      osc.connect(amp).connect(this.out());
      osc.start(time);
      osc.stop(time + 0.3);
    }
  }
}