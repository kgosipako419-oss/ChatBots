"""Offline text-to-speech using pyttsx3 (Windows SAPI voices)."""
from __future__ import annotations

from .. import config


class Speaker:
    def __init__(self) -> None:
        import pyttsx3  # lazy import

        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", config.get("tts.rate", 180))

        # Pick the preferred voice. "en-gb"/"uk" selects whichever British voice is
        # installed (Hazel/George/Susan), matched by various id/name spellings.
        # Otherwise match the given text against the voice name or id. Falls back to
        # the system default if nothing matches.
        voice_pref = config.get("tts.voice")
        if voice_pref:
            pref = voice_pref.lower()
            uk_markers = ["en-gb", "engb", "en_gb", "hazel", "george", "susan"]
            for voice in self.engine.getProperty("voices"):
                haystack = f"{voice.name} {voice.id or ''}".lower()
                is_match = (any(m in haystack for m in uk_markers)
                            if pref in ("en-gb", "uk", "gb") else pref in haystack)
                if is_match:
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
