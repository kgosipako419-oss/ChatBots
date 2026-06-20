"""Shared mode flags set by tools and read by the main voice loop.

Lets a tool (which can only return a string) request that the loop switch into a
sub-mode, e.g. dictation. The loop polls and clears these.
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
_dictation_requested = False


def request_dictation() -> None:
    global _dictation_requested
    with _lock:
        _dictation_requested = True


def take_dictation_request() -> bool:
    """Return True once if dictation was requested, then clear the flag."""
    global _dictation_requested
    with _lock:
        val = _dictation_requested
        _dictation_requested = False
    return val
