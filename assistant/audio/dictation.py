"""Continuous speak-to-type dictation loop.

Records short utterances, transcribes them, and either types the text into the
focused field or executes a spoken editing command (new line, delete that, etc.).
Runs until the user says a stop phrase.
"""
from __future__ import annotations

from typing import Callable

STOP_PHRASES = {
    "stop dictation", "stop dictating", "end dictation", "stop listening", "that's all",
    "stop taking dictation", "finish dictation",
}


def run_dictation(record_fn: Callable[[], object],
                  transcribe_fn: Callable[[object], str],
                  speak_fn: Callable[[str], None]) -> None:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
    except Exception:
        speak_fn("Dictation needs the pyautogui package.")
        return

    speak_fn("Dictation on.")
    while True:
        audio = record_fn()
        text = transcribe_fn(audio).strip()
        if not text:
            continue
        norm = text.lower().strip(" .!?,")
        print(f"[dictation] {text}")

        if norm in STOP_PHRASES:
            speak_fn("Dictation off.")
            return
        if norm in ("new line", "newline", "line break"):
            pyautogui.press("enter")
            continue
        if norm in ("new paragraph", "paragraph"):
            pyautogui.press("enter"); pyautogui.press("enter")
            continue
        if norm in ("delete that", "scratch that", "delete last word", "delete"):
            pyautogui.hotkey("ctrl", "backspace")
            continue
        if norm in ("undo", "undo that"):
            pyautogui.hotkey("ctrl", "z")
            continue
        if norm in ("select all",):
            pyautogui.hotkey("ctrl", "a")
            continue

        # Otherwise, type what was said. Whisper already adds most punctuation.
        pyautogui.write(text + " ", interval=0.005)
