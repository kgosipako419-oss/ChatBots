"""Microphone capture with energy-based silence detection.

Records a command: starts buffering once the user begins speaking and stops after
a configurable stretch of trailing silence (or a hard time cap).
"""
from __future__ import annotations

import numpy as np
import sounddevice as sd

from .. import config

SAMPLE_RATE = 16_000   # what faster-whisper and openwakeword expect
FRAME = 1280           # 80 ms frames at 16 kHz


def _rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(block, dtype=np.float64)) + 1e-12))


def record_until_silence() -> np.ndarray:
    """Capture a single spoken command. Returns float32 mono audio at 16 kHz."""
    threshold = config.get("audio.silence_threshold", 0.012)
    silence_secs = config.get("audio.silence_duration", 1.0)
    max_secs = config.get("audio.max_record_seconds", 15)
    device = config.get("audio.input_device", None)

    frames: list[np.ndarray] = []
    silent_frames = 0
    started = False
    elapsed = 0.0
    frame_secs = FRAME / SAMPLE_RATE
    silence_limit = int(silence_secs / frame_secs)
    # How long to wait for the user to START speaking before giving up.
    start_secs = config.get("audio.command_start_timeout", 7)
    start_timeout = int(start_secs / frame_secs)
    waited = 0

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=FRAME, device=device) as stream:
        while elapsed < max_secs:
            block, _overflow = stream.read(FRAME)
            block = block.reshape(-1)
            level = _rms(block)
            elapsed += frame_secs

            if not started:
                waited += 1
                if level >= threshold:
                    started = True
                    elapsed = 0.0  # max_record_seconds applies to speech, not the wait
                    frames.append(block.copy())
                elif waited >= start_timeout:
                    break  # user never spoke
                continue

            frames.append(block.copy())
            if level < threshold:
                silent_frames += 1
                if silent_frames >= silence_limit:
                    break
            else:
                silent_frames = 0

    if not frames:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(frames).astype(np.float32)


def list_devices() -> str:
    """Return a human-readable list of input devices and their indices."""
    lines = []
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            lines.append(f"  [{idx}] {dev['name']}")
    return "Input devices:\n" + "\n".join(lines)
