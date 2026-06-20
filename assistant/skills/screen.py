"""The assistant's 'eyes': read the screen and describe the UI aloud.

Primary source is UI Automation (accurate, structured). OCR is the fallback for
content that isn't exposed to accessibility.
"""
from __future__ import annotations

from ..brain.tools import tool
from .. import automation as A


@tool(
    "describe_screen",
    "Describe what's currently on screen: the active window and the buttons, links "
    "and fields the user can interact with. Use when the user asks what's on screen.",
    {"type": "object", "properties": {}},
)
def describe_screen() -> str:
    title = A.window_title() if A.available() else None
    parts: list[str] = []
    if title:
        parts.append(f"You're in {title}.")
    elements = A.list_interactive(20) if A.available() else []
    if elements:
        names = [n for n, _t in elements]
        parts.append(f"I can see {len(names)} things to interact with, including: "
                     + ", ".join(names[:10]) + ".")
    else:
        # Fall back to reading on-screen text.
        try:
            from .. import ocr
            text = ocr.screen_text()
            if text:
                parts.append("On screen: " + text[:600])
        except Exception:
            pass
    return " ".join(parts) if parts else "I couldn't read the screen."


@tool(
    "read_screen",
    "Read the text currently visible on screen aloud (uses OCR). Use for reading a "
    "document, web page, or anything on screen.",
    {"type": "object", "properties": {}},
)
def read_screen() -> str:
    try:
        from .. import ocr
        text = ocr.screen_text()
    except Exception as exc:
        return f"I couldn't read the screen: {exc}"
    if not text:
        return "I don't see any readable text on screen."
    return text


@tool(
    "read_focused_element",
    "Say which control currently has keyboard focus and its contents. Useful to "
    "confirm where typing will go.",
    {"type": "object", "properties": {}},
)
def read_focused_element() -> str:
    if not A.available():
        return "Accessibility reading isn't available."
    ctrl = A.focused_control()
    if ctrl is None:
        return "Nothing seems to have focus right now."
    name = A._name_of(ctrl)
    ctype = A._type_of(ctrl).replace("Control", "")
    value = ""
    try:
        value = ctrl.GetValuePattern().Value or ""
    except Exception:
        pass
    bits = []
    if name:
        bits.append(f"Focus is on '{name}'")
    else:
        bits.append("Focus is on an unnamed element")
    if ctype:
        bits.append(f"a {ctype}")
    if value:
        bits.append(f"containing '{value}'")
    return ", ".join(bits) + "."


@tool(
    "find_on_screen",
    "Check whether some text is visible on screen and roughly where it is.",
    {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to look for"}},
        "required": ["text"],
    },
)
def find_on_screen(text: str) -> str:
    try:
        from .. import ocr
        items = ocr.screen_items()
    except Exception as exc:
        return f"I couldn't scan the screen: {exc}"
    needle = text.strip().lower()
    for it in items:
        if needle in it["text"].lower():
            x, y = it["center"]
            third_h = "top" if y < 360 else "bottom" if y > 720 else "middle"
            third_w = "left" if x < 640 else "right" if x > 1280 else "center"
            return f"Yes, I see '{it['text']}' in the {third_h} {third_w} of the screen."
    return f"I don't see '{text}' on screen."
