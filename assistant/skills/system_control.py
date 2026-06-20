"""System utility skills: screen brightness and clipboard."""
from __future__ import annotations

from ..brain.tools import tool

try:
    import screen_brightness_control as sbc
    _HAS_SBC = True
except Exception:
    _HAS_SBC = False

try:
    import pyperclip
    _HAS_CLIP = True
except Exception:
    _HAS_CLIP = False


@tool(
    "set_brightness",
    "Set the screen brightness to a level from 0 to 100.",
    {
        "type": "object",
        "properties": {"level": {"type": "integer", "description": "Brightness 0-100"}},
        "required": ["level"],
    },
)
def set_brightness(level: int) -> str:
    if not _HAS_SBC:
        return "Brightness control needs the screen_brightness_control package."
    level = max(0, min(100, int(level)))
    try:
        sbc.set_brightness(level)
        return f"Brightness set to {level} percent."
    except Exception as exc:
        return f"Could not set brightness: {exc}"


@tool(
    "get_brightness",
    "Get the current screen brightness level.",
    {"type": "object", "properties": {}},
)
def get_brightness() -> str:
    if not _HAS_SBC:
        return "Brightness control needs the screen_brightness_control package."
    try:
        values = sbc.get_brightness()
        level = values[0] if isinstance(values, list) else values
        return f"Brightness is at {level} percent."
    except Exception as exc:
        return f"Could not read brightness: {exc}"


@tool(
    "read_clipboard",
    "Read and return the current text contents of the clipboard.",
    {"type": "object", "properties": {}},
)
def read_clipboard() -> str:
    if not _HAS_CLIP:
        return "Clipboard access needs the pyperclip package."
    text = pyperclip.paste()
    if not text:
        return "The clipboard is empty."
    return f"Clipboard contains: {text}"


@tool(
    "set_clipboard",
    "Copy the given text onto the clipboard.",
    {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to copy"}},
        "required": ["text"],
    },
)
def set_clipboard(text: str) -> str:
    if not _HAS_CLIP:
        return "Clipboard access needs the pyperclip package."
    pyperclip.copy(text)
    return "Copied to the clipboard."
