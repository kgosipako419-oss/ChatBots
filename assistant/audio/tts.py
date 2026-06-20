"""Offline text-to-speech using pyttsx3 (Windows SAPI voices)."""
from __future__ import annotations

from .. import config


class Speaker:
    def __init__(self) -> None:
        import pyttsx3  # lazy import

        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", config.get("tts.rate", 180))

        voice_pref = config.get("tts.voice")
        if voice_pref:
            for voice in self.engine.getProperty("voices"):
                if voice_pref.lower() in voice.name.lower():
                    self.engine.setProperty("voice", voice.id)
                    break

    def say(self, text: str) -> None:
        if not text:
            return
        self.engine.say(text)
        self.engine.runAndWait()

    @staticmethod
    def list_voices() -> str:
        import pyttsx3

        engine = pyttsx3.init()
        names = [v.name for v in engine.getProperty("voices")]
        return "Available voices: " + ", ".join(names)
