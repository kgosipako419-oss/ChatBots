"""Timers and reminders that fire in the background.

When a timer/reminder elapses it is announced: printed, spoken (if the voice loop
registered an announcer), and pushed to your phone (if ntfy is configured).
"""
from __future__ import annotations

import datetime as _dt
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from ..brain.tools import tool

# The voice loop calls set_announcer() with a function that speaks text aloud.
_announcer: Optional[Callable[[str], None]] = None


def set_announcer(fn: Callable[[str], None]) -> None:
    global _announcer
    _announcer = fn


def _announce(message: str) -> None:
    print(f"\n[reminder] {message}\n")
    if _announcer is not None:
        try:
            _announcer(message)
        except Exception:
            pass
    try:  # best-effort phone push
        from .notifications import send_phone_notification
        send_phone_notification(message=message, title="Reminder")
    except Exception:
        pass


@dataclass
class _Timer:
    id: int
    label: str
    fire_at: _dt.datetime
    handle: threading.Timer


_timers: dict[int, _Timer] = {}
_next_id = 1
_lock = threading.Lock()


def _schedule(label: str, delay_seconds: float, spoken: str) -> int:
    global _next_id
    with _lock:
        tid = _next_id
        _next_id += 1

    def fire() -> None:
        with _lock:
            _timers.pop(tid, None)
        _announce(spoken)

    handle = threading.Timer(max(0.0, delay_seconds), fire)
    handle.daemon = True
    handle.start()
    with _lock:
        _timers[tid] = _Timer(tid, label,
                              _dt.datetime.now() + _dt.timedelta(seconds=delay_seconds), handle)
    return tid


@tool(
    "set_timer",
    "Set a countdown timer for a number of minutes. Announces when it finishes.",
    {
        "type": "object",
        "properties": {
            "minutes": {"type": "number", "description": "Minutes until the timer goes off"},
            "label": {"type": "string", "description": "Optional name for the timer"},
        },
        "required": ["minutes"],
    },
)
def set_timer(minutes: float, label: str = "") -> str:
    label = label or "timer"
    spoken = f"Your {label} is up." if label != "timer" else "Your timer is up."
    _schedule(label, float(minutes) * 60, spoken)
    return f"Timer set for {minutes:g} minute{'s' if minutes != 1 else ''}."


@tool(
    "set_reminder",
    "Set a reminder. Provide either in_minutes (relative) or at_time (clock time like "
    "'17:30' or '5:30 pm'). The message is announced when it's due.",
    {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "What to remind about"},
            "in_minutes": {"type": "number", "description": "Minutes from now"},
            "at_time": {"type": "string", "description": "Clock time, e.g. '17:30' or '5:30 pm'"},
        },
        "required": ["message"],
    },
)
def set_reminder(message: str, in_minutes: float | None = None,
                 at_time: str | None = None) -> str:
    spoken = f"Reminder: {message}"
    if in_minutes is not None:
        _schedule(message, float(in_minutes) * 60, spoken)
        return f"I'll remind you in {in_minutes:g} minute{'s' if in_minutes != 1 else ''}."
    if at_time:
        target = _parse_time(at_time)
        if target is None:
            return f"I couldn't understand the time '{at_time}'. Try '17:30' or '5:30 pm'."
        delay = (target - _dt.datetime.now()).total_seconds()
        _schedule(message, delay, spoken)
        return f"I'll remind you at {target.strftime('%I:%M %p').lstrip('0')}."
    return "Tell me when: either in_minutes or at_time."


def _parse_time(text: str) -> _dt.datetime | None:
    text = text.strip().lower().replace(".", "")
    now = _dt.datetime.now()
    for fmt in ("%H:%M", "%I:%M %p", "%I %p", "%I:%M%p", "%I%p"):
        try:
            t = _dt.datetime.strptime(text, fmt).time()
        except ValueError:
            continue
        target = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        if target <= now:  # already passed today -> tomorrow
            target += _dt.timedelta(days=1)
        return target
    return None


@tool(
    "list_timers",
    "List active timers and reminders and when they will go off.",
    {"type": "object", "properties": {}},
)
def list_timers() -> str:
    with _lock:
        active = list(_timers.values())
    if not active:
        return "No active timers or reminders."
    parts = [f"{t.label} at {t.fire_at.strftime('%I:%M %p').lstrip('0')}" for t in active]
    return "Active: " + "; ".join(parts) + "."


@tool(
    "cancel_timer",
    "Cancel timers/reminders. Pass 'all', a timer id number, or a label to match.",
    {
        "type": "object",
        "properties": {"which": {"type": "string", "description": "'all', an id, or a label"}},
        "required": ["which"],
    },
)
def cancel_timer(which: str) -> str:
    which = str(which).strip().lower()
    with _lock:
        to_cancel = []
        for t in _timers.values():
            if which == "all" or which == str(t.id) or which in t.label.lower():
                to_cancel.append(t)
        for t in to_cancel:
            t.handle.cancel()
            _timers.pop(t.id, None)
    if not to_cancel:
        return "No matching timers to cancel."
    return f"Cancelled {len(to_cancel)} timer{'s' if len(to_cancel) != 1 else ''}."
