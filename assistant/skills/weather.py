"""Weather via wttr.in (no API key required; needs internet)."""
from __future__ import annotations

import requests

from ..brain.tools import tool


@tool(
    "get_weather",
    "Get the current weather for a location (city name). Leave blank to use your "
    "approximate location based on your IP address.",
    {
        "type": "object",
        "properties": {"location": {"type": "string", "description": "City name, optional"}},
    },
)
def get_weather(location: str = "") -> str:
    place = location.strip()
    # format=4 gives e.g. "London: ⛅️ +12°C ..." — concise and spoken-friendly.
    url = f"https://wttr.in/{place}?format=%l:+%C+%t,+feels+like+%f,+wind+%w"
    try:
        resp = requests.get(url, headers={"User-Agent": "curl/8"}, timeout=10)
        resp.raise_for_status()
        text = resp.text.strip()
        if not text or "Unknown location" in text:
            return f"I couldn't find weather for '{location}'."
        return text
    except Exception as exc:
        return f"Could not get the weather: {exc}"
