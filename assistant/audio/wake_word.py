"""Wake-word detection with two backends:

- openWakeWord: fast, low-CPU, but only for pretrained words
  (hey_jarvis, alexa, hey_mycroft, hey_rhasspy).
- Whisper spotter: works for ANY custom word (e.g. "puddles") by transcribing
  short speech bursts and fuzzy-matching the word. No training required.

`make_detector()` picks the right backend automatically based on config.
"""
from __future__ import annotations

import numpy as np
import sounddevice as sd

from .. import config

SAMPLE_RATE = 16_000
FRAME = 1280  # 80 ms

# Words openWakeWord ships pretrained models for.
PRETRAINED = {"hey_jarvis", "alexa", "hey_mycroft", "hey_rhasspy", "timer", "weather"}


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class OpenWakeWordDetector:
    """Low-CPU detection for pretrained wake words."""

    def __init__(self, threshold: float = 0.5) -> None:
        from openwakeword.model import Model

        try:
            import openwakeword
            openwakeword.utils.download_models()
        except Exception:
            pass

        self.wake_word = config.get("assistant.wake_word", "hey_jarvis")
        self.threshold = threshold
        self.device = config.get("audio.input_device", None)
        self.model = Model(wakeword_models=[self.wake_word], inference_framework="onnx")

    def wait_for_wake(self) -> str:
        self.model.reset()
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                            blocksize=FRAME, device=self.device) as stream:
            while True:
                block, _ = stream.read(FRAME)
                audio = np.frombuffer(block, dtype=np.int16)
                scores = self.model.predict(audio)
                if any(s >= self.threshold for s in scores.values()):
                    return ""  # openWakeWord gives no transcript, so no inline command


class WhisperWakeDetector:
    """Custom-word detection via short-burst Whisper transcription.

    Idle is cheap (only audio energy is measured); the Whisper model only runs on
    bursts of speech, then we check whether the wake word was said.

    If `shared_model` is provided (the main STT model), it is reused — no second
    model load or download. Otherwise the configured wake model is loaded, falling
    back to the main STT model name if the wake model isn't available offline.
    """

    def __init__(self, shared_model=None) -> None:
        self.word = config.get("assistant.wake_word", "puddles").lower().replace("_", " ").strip()
        self.device = config.get("audio.input_device", None)
        self.threshold = config.get("audio.silence_threshold", 0.012)

        if shared_model is not None:
            self.model = shared_model
        else:
            from faster_whisper import WhisperModel
            kwargs = dict(device=config.get("stt.device", "cpu"),
                          compute_type=config.get("stt.compute_type", "int8"))
            try:
                self.model = WhisperModel(config.get("stt.wake_model", "tiny.en"), **kwargs)
            except Exception:
                # Offline / download failed: reuse the main STT model instead.
                self.model = WhisperModel(config.get("stt.model", "base.en"), **kwargs)
        # Acceptable transcriptions: the word, its tokens, configured aliases (other
        # spellings the STT may produce), and near-misses handled in _matches().
        self._targets = set(self.word.split())
        self._targets.add(self.word)
        for alias in (config.get("assistant.wake_word_aliases", []) or []):
            a = str(alias).lower().strip()
            if a:
                self._targets.add(a)

    def _matches(self, text: str) -> bool:
        norm = "".join(c if c.isalnum() or c.isspace() else " " for c in text.lower())
        if self.word in norm:
            return True
        # Whisper mishears short single words a lot; be forgiving (2 edits for long words).
        tol = 2 if len(self.word) >= 6 else 1
        for tok in norm.split():
            for target in self._targets:
                if abs(len(tok) - len(target)) <= tol and _levenshtein(tok, target) <= tol:
                    return True
        return False

    def _capture_burst(self, stream) -> np.ndarray:
        """Wait for speech, then capture until a short pause. Long enough to hold a
        whole 'Ekko, do something' sentence, but a bare 'Ekko' still ends quickly."""
        frame_secs = FRAME / SAMPLE_RATE
        frames: list[np.ndarray] = []
        started = False
        silent = 0
        elapsed = 0.0
        while elapsed < 6.0:
            block, _ = stream.read(FRAME)
            block = block.reshape(-1)
            level = float(np.sqrt(np.mean(block.astype(np.float64) ** 2) + 1e-12))
            elapsed += frame_secs
            if not started:
                if level >= self.threshold:
                    started = True
                    frames.append(block.copy())
                continue
            frames.append(block.copy())
            if level < self.threshold:
                silent += 1
                if silent >= int(0.4 / frame_secs):
                    break
            else:
                silent = 0
        if not frames:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(frames).astype(np.float32)

    def wait_for_wake(self) -> str:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            blocksize=FRAME, device=self.device) as stream:
            while True:
                burst = self._capture_burst(stream)
                if burst.size < SAMPLE_RATE // 3:  # ignore <0.33s blips
                    continue
                segments, _ = self.model.transcribe(burst, language="en", beam_size=1)
                text = " ".join(s.text for s in segments).strip()
                if text:
                    matched = self._matches(text)
                    print(f"[heard: {text!r}{'  <- WAKE' if matched else ''}]", flush=True)
                    if matched:
                        return text

    def split_command(self, trigger_text: str) -> str:
        """Given the wake transcript, return any command spoken in the same breath.
        'Ekko, what time is it' -> 'what time is it'; bare 'Ekko' -> ''."""
        def norm(w: str) -> str:
            return "".join(c for c in w.lower() if c.isalnum())

        targets = {norm(t) for t in self._targets if norm(t)}
        words = trigger_text.split()
        cut = -1
        for i, w in enumerate(words):
            nw = norm(w)
            if nw in targets or any(_levenshtein(nw, t) <= 1 for t in targets):
                cut = i  # last wake-token position
        if cut == -1:
            return ""
        return " ".join(words[cut + 1:]).strip(" ,.!?")


def make_detector(shared_model=None):
    """Choose a backend based on config. 'auto' uses openWakeWord for pretrained
    words and the Whisper spotter for anything custom. `shared_model` (the main STT
    model) is reused by the Whisper spotter to avoid a second load/download."""
    word = config.get("assistant.wake_word", "puddles")
    engine = config.get("assistant.wake_word_engine", "auto")
    if engine == "openwakeword" or (engine == "auto" and word in PRETRAINED):
        return OpenWakeWordDetector()
    return WhisperWakeDetector(shared_model=shared_model)
