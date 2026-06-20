"""Offline speech-to-text using faster-whisper."""
from __future__ import annotations

import numpy as np

from .. import config


class Transcriber:
    def __init__(self) -> None:
        from faster_whisper import WhisperModel  # lazy: heavy import

        model = config.get("stt.model", "base.en")
        device = config.get("stt.device", "cpu")
        compute_type = config.get("stt.compute_type", "int8")
        self.model = WhisperModel(model, device=device, compute_type=compute_type)

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        segments, _info = self.model.transcribe(
            audio, language="en", vad_filter=True, beam_size=1
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
