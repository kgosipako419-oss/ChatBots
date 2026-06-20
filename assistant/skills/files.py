"""File and folder skills: open common folders, search for files, play on YouTube."""
from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

from ..brain.tools import tool

HOME = Path.home()
KNOWN_FOLDERS = {
    "downloads": HOME / "Downloads",
    "documents": HOME / "Documents",
    "desktop": HOME / "Desktop",
    "pictures": HOME / "Pictures",
    "music": HOME / "Music",
    "videos": HOME / "Videos",
    "home": HOME,
}


@tool(
    "open_folder",
    "Open a folder in File Explorer. Common names: downloads, documents, desktop, "
    "pictures, music, videos, home. You may also pass a full path.",
    {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Folder name or path"}},
        "required": ["name"],
    },
)
def open_folder(name: str) -> str:
    key = name.strip().lower()
    folder = KNOWN_FOLDERS.get(key)
    if folder is None:
        folder = Path(name).expanduser()
    if not folder.exists():
        return f"Couldn't find the folder '{name}'."
    os.startfile(str(folder))  # type: ignore[attr-defined]
    return f"Opened {folder.name or folder}."


@tool(
    "search_files",
    "Search for files whose name contains the query, within a common folder "
    "(downloads, documents, desktop, pictures, music, videos, or home).",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text to find in file names"},
            "location": {"type": "string",
                         "description": "Folder to search (default: home)"},
        },
        "required": ["query"],
    },
)
def search_files(query: str, location: str = "home") -> str:
    root = KNOWN_FOLDERS.get(location.strip().lower(), HOME)
    needle = query.strip().lower()
    matches: list[str] = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden/system dirs to keep it fast.
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fname in filenames:
            scanned += 1
            if needle in fname.lower():
                matches.append(fname)
                if len(matches) >= 10:
                    break
            if scanned > 50_000:  # safety cap
                break
        if len(matches) >= 10 or scanned > 50_000:
            break
    if not matches:
        return f"No files matching '{query}' found in {location}."
    return f"Found {len(matches)}: " + ", ".join(matches) + "."


@tool(
    "play_youtube",
    "Search YouTube for a video, song, or query and open the results in the browser.",
    {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "What to play/search on YouTube"}},
        "required": ["query"],
    },
)
def play_youtube(query: str) -> str:
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
    return f"Opening YouTube for {query}."
