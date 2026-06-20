"""Simple persistent notes, stored in notes.txt in the project folder."""
from __future__ import annotations

import datetime as _dt

from ..brain.tools import tool
from ..config import PROJECT_ROOT

NOTES_FILE = PROJECT_ROOT / "notes.txt"


@tool(
    "add_note",
    "Save a note or to-do item for later.",
    {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "The note to save"}},
        "required": ["text"],
    },
)
def add_note(text: str) -> str:
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(NOTES_FILE, "a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {text}\n")
    return "Noted."


@tool(
    "read_notes",
    "Read back all saved notes.",
    {"type": "object", "properties": {}},
)
def read_notes() -> str:
    if not NOTES_FILE.exists():
        return "You don't have any notes yet."
    lines = [ln.strip() for ln in NOTES_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return "You don't have any notes yet."
    # Strip the timestamps for a cleaner spoken read-back.
    cleaned = [ln.split("] ", 1)[-1] for ln in lines]
    return f"You have {len(cleaned)} note{'s' if len(cleaned) != 1 else ''}: " + "; ".join(cleaned)


@tool(
    "clear_notes",
    "Delete all saved notes.",
    {"type": "object", "properties": {}},
    dangerous=True,
)
def clear_notes() -> str:
    if NOTES_FILE.exists():
        NOTES_FILE.unlink()
    return "All notes cleared."
