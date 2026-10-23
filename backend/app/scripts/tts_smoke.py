"""Real Piper smoke test — the release gate for "TTS actually works".

    python -m app.scripts.tts_smoke --voices-dir backend\\storage\\models --out backend\\storage\\audio\\smoke

Synthesizes one battle line per voice, validates the WAV headers, prints size,
duration and timing, and exits non-zero on any failure. Uses the production
adapter, not a stub.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import os
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

from app.providers.tts.piper_adapter import PiperTTSProvider
from app.providers.tts.voices import PIPER_VOICES

LINES = {
    "en_US-kristin-medium": (
        "Oh honey, hold my spark — my flow about antennas is bright,\n"
        "You said chrome, I said chrome, and I still won tonight."
    ),
    "en_US-joe-medium": (
        "Sure. You brought sparkle. I brought a point.\n"
        "That was almost a rhyme. Try again."
    ),
}

MIN_BYTES = 10_000
MIN_SECONDS = 0.8


def peak_rss_mb() -> float:
    """Best-effort peak RSS. ``resource`` is unavailable on Windows, so use psutil
    when present and fall back to the Windows working-set API."""
    try:
        import psutil  # optional, not a required dependency

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        pass
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            # The handle must be declared as HANDLE or it is truncated to 32 bits.
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.K32GetProcessMemoryInfo.argtypes = [
                wintypes.HANDLE,
                ctypes.c_void_p,
                wintypes.DWORD,
            ]
            kernel32.K32GetProcessMemoryInfo.restype = wintypes.BOOL

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)
            if kernel32.K32GetProcessMemoryInfo(
                kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
            ):
                return counters.PeakWorkingSetSize / (1024 * 1024)
        except Exception:
            pass
    return 0.0


def inspect_wav(data: bytes) -> dict:
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("Not a RIFF/WAVE file")
    with wave.open(io.BytesIO(data), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.getnframes()
    duration = frames / rate if rate else 0.0
    return {
        "channels": channels,
        "sample_width": width,
        "rate": rate,
        "frames": frames,
        "seconds": duration,
    }


async def run(voices_dir: Path, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    provider = PiperTTSProvider(voices_dir=voices_dir, timeout_seconds=120)

    missing = [vid for vid in LINES if not provider.voice_available(vid)]
    if missing:
        print("Missing voice models:", ", ".join(missing), file=sys.stderr)
        print(
            "Download them with:\n  python -m piper.download_voices "
            f"{' '.join(missing)} --download-dir {voices_dir}",
            file=sys.stderr,
        )
        return 1

    failures = 0
    for voice in PIPER_VOICES:
        text = LINES[voice.id]
        label = voice.id.replace("en_US-", "").replace("-medium", "")
        print(f"\n== {voice.id} ==")
        started = time.perf_counter()
        try:
            result = await provider.synthesize(text, voice.id)
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
            failures += 1
            continue
        elapsed = time.perf_counter() - started

        info = inspect_wav(result.data)
        target = out_dir / f"smoke-{label}.wav"
        target.write_bytes(result.data)

        checks = {
            f"size >= {MIN_BYTES} bytes": len(result.data) >= MIN_BYTES,
            "PCM 16-bit mono": info["channels"] == 1 and info["sample_width"] == 2,
            "sample rate 22050": info["rate"] == 22050,
            f"duration >= {MIN_SECONDS}s": info["seconds"] >= MIN_SECONDS,
        }
        for name, passed in checks.items():
            print(f"  [{'ok' if passed else 'FAIL'}] {name}")
            if not passed:
                failures += 1

        print(f"  file:      {target}")
        print(f"  bytes:     {len(result.data):,}")
        print(f"  duration:  {info['seconds']:.2f}s @ {info['rate']} Hz")
        print(f"  synth:     {elapsed * 1000:.0f} ms")

        if shutil.which("ffprobe"):
            probe = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries",
                    "stream=codec_name,sample_rate,channels,duration",
                    "-of", "default=noprint_wrappers=1", str(target),
                ],
                capture_output=True,
                text=True,
            )
            if probe.returncode == 0:
                print("  ffprobe:   " + " ".join(probe.stdout.split()))

    print(f"\nPeak RSS: {peak_rss_mb():.1f} MB")
    if failures:
        print(f"\n{failures} check(s) failed.", file=sys.stderr)
        return 1
    print("\nAll TTS checks passed — real audio generated for both voices.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify real Piper TTS output")
    parser.add_argument("--voices-dir", default="backend/storage/models")
    parser.add_argument("--out", default="backend/storage/audio/smoke")
    args = parser.parse_args(argv)
    return asyncio.run(run(Path(args.voices_dir).resolve(), Path(args.out).resolve()))


if __name__ == "__main__":
    raise SystemExit(main())