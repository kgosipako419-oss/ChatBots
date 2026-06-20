"""The assistant's 'hands': operate the UI by name, not by pixel guessing.

Uses UI Automation to click/focus named elements. Falls back to OCR + a real
mouse click for things the accessibility tree doesn't expose.
"""
from __future__ import annotations

from ..brain.tools import tool
from .. import automation as A

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pyautogui = None


@tool(
    "click_element",
    "Click a button, link, menu item, or checkbox on screen by its name/label "
    "(e.g. 'Submit', 'File', 'Sign in'). This is the main way to operate apps by voice.",
    {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Visible name of the element"}},
        "required": ["name"],
    },
)
def click_element(name: str) -> str:
    if A.available():
        ctrl = A.find_by_name(name, interactive_only=True)
        if ctrl is not None and A.invoke(ctrl):
            return f"Clicked {A._name_of(ctrl) or name}."
    # Fallback: find the text on screen and click it.
    return _click_text_fallback(name, label=name)


@tool(
    "click_text",
    "Click on a piece of visible text on screen (OCR-based). Use when click_element "
    "can't find a named control.",
    {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Visible text to click"}},
        "required": ["text"],
    },
)
def click_text(text: str) -> str:
    return _click_text_fallback(text, label=text)


def _click_text_fallback(text: str, label: str) -> str:
    if pyautogui is None:
        return "Clicking needs the pyautogui package."
    try:
        from .. import ocr
        items = ocr.screen_items()
    except Exception as exc:
        return f"I couldn't locate '{label}': {exc}"
    needle = text.strip().lower()
    best = None
    for it in items:
        if needle == it["text"].lower():
            best = it
            break
        if best is None and needle in it["text"].lower():
            best = it
    if best is None:
        return f"I couldn't find '{label}' on screen to click."
    x, y = best["center"]
    pyautogui.click(int(x), int(y))
    return f"Clicked '{best['text']}'."


@tool(
    "focus_field",
    "Put the keyboard focus into a text field by its label, so the user can type or dictate into it.",
    {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Label of the field"}},
        "required": ["name"],
    },
)
def focus_field(name: str) -> str:
    if not A.available():
        return "Accessibility control isn't available."
    ctrl = A.find_by_name(name, interactive_only=True)
    if ctrl is None:
        return f"I couldn't find a field called '{name}'."
    if A.focus(ctrl):
        return f"Focused the '{A._name_of(ctrl) or name}' field. Go ahead."
    return f"I found '{name}' but couldn't focus it."


@tool(
    "type_into_field",
    "Type text into a named text field (focuses it first). Good for forms.",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Label of the field"},
            "text": {"type": "string", "description": "Text to enter"},
        },
        "required": ["name", "text"],
    },
)
def type_into_field(name: str, text: str) -> str:
    if not A.available():
        return "Accessibility control isn't available."
    ctrl = A.find_by_name(name, interactive_only=True)
    if ctrl is None:
        return f"I couldn't find a field called '{name}'."
    if A.set_value(ctrl, text):
        return f"Entered text into '{A._name_of(ctrl) or name}'."
    return f"I couldn't type into '{name}'."


@tool(
    "list_clickable",
    "List the buttons, links and controls you can click in the current window.",
    {"type": "object", "properties": {}},
)
def list_clickable() -> str:
    if not A.available():
        return "Accessibility reading isn't available."
    elements = A.list_interactive(25)
    if not elements:
        return "I don't see any named controls in this window."
    return "You can interact with: " + ", ".join(n for n, _t in elements) + "."


@tool(
    "scroll_page",
    "Scroll the current window up or down.",
    {
        "type": "object",
        "properties": {
            "direction": {"type": "string", "enum": ["up", "down"]},
            "amount": {"type": "integer", "description": "How much to scroll (default 3)"},
        },
        "required": ["direction"],
    },
)
def scroll_page(direction: str, amount: int = 3) -> str:
    if pyautogui is None:
        return "Scrolling needs the pyautogui package."
    clicks = 400 * max(1, int(amount))
    pyautogui.scroll(clicks if direction == "up" else -clicks)
    return f"Scrolled {direction}."
