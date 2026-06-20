"""Push notifications to your phone via ntfy (https://ntfy.sh).

Setup: install the ntfy app on your phone, subscribe to a long secret topic name,
then put that topic in config.yaml under notifications.ntfy_topic.
"""
from __future__ import annotations

import requests

from .. import config
from ..brain.tools import tool


@tool(
    "send_phone_notification",
    "Send a push notification to the user's phone. Use for reminders or to send info to their phone.",
    {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Notification body text"},
            "title": {"type": "string", "description": "Optional notification title"},
            "priority": {
                "type": "string",
                "enum": ["min", "low", "default", "high", "urgent"],
                "description": "Notification priority",
            },
        },
        "required": ["message"],
    },
)
def send_phone_notification(message: str, title: str = "Assistant",
                            priority: str = "default") -> str:
    server = config.get("notifications.ntfy_server", "https://ntfy.sh").rstrip("/")
    topic = config.get("notifications.ntfy_topic", "")
    if not topic:
        return ("No ntfy topic configured. Set notifications.ntfy_topic in config.yaml "
                "and subscribe to it in the ntfy phone app.")
    try:
        requests.post(
            f"{server}/{topic}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": priority},
            timeout=10,
        )
        return "Sent the notification to your phone."
    except Exception as exc:
        return f"Could not send notification: {exc}"
