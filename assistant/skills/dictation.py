"""Dictation: compose text by speaking. The tool requests dictation; the voice
loop then enters a continuous speak-to-type sub-mode until you say 'stop dictation'.
"""
from __future__ import annotations

from ..brain.tools import tool
from .. import modes


@tool(
    "start_dictation",
    "Begin dictation mode so the user can speak text and have it typed into the "
    "focused field. Use when the user says things like 'take dictation', 'let me "
    "dictate', or 'type what I say'.",
    {"type": "object", "properties": {}},
)
def start_dictation() -> str:
    modes.request_dictation()
    return ("Dictation starting. Speak naturally and I'll type it. Say 'new line' or "
            "'new paragraph' for breaks, and 'stop dictation' when you're done.")
