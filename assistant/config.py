"""Configuration loading with sensible defaults.

Loads `config.yaml` from the project root if present, otherwise falls back to
defaults. Access via the module-level `CONFIG` dict or `get("a.b.c", default)`.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

DEFAULTS: dict[str, Any] = {
    "assistant": {
        "name": "Ekko",
        "wake_word": "ekko",
        # Extra spellings the speech-to-text might produce for the same spoken word.
        "wake_word_aliases": ["echo", "ecko", "eko", "echo."],
        "wake_word_engine": "auto",       # auto | openwakeword | whisper
        "require_confirmation_for_dangerous": True,
        "conversation_follow_up": False,  # keep listening for follow-ups after a reply
        "hands_free": False,              # True = always listening, no wake word (blind/no-hands use)
    },
    "llm": {
        "host": "http://localhost:11434",
        "model": "qwen2.5:3b",
        "temperature": 0.3,
        "num_ctx": 4096,
        "timeout": 300,          # seconds; first load on a small GPU can be slow
        "keep_alive": "30m",     # keep the model in memory so replies stay fast
    },
    "stt": {"model": "base.en", "wake_model": "tiny.en", "device": "cpu", "compute_type": "int8"},
    "tts": {"voice": None, "rate": 180},
    "audio": {
        "input_device": None,
        "silence_threshold": 0.012,
        "silence_duration": 1.0,
        "max_record_seconds": 15,
        "command_start_timeout": 7,   # seconds to wait for you to start speaking after "Yes?"
    },
    "notifications": {"ntfy_server": "https://ntfy.sh", "ntfy_topic": ""},
    "remote_hosts": {},
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge `override` into a copy of `base`."""
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict[str, Any]:
    user_config: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            user_config = yaml.safe_load(fh) or {}
    merged = _deep_merge(DEFAULTS, user_config)

    # Allow secrets via environment variables (override file).
    if os.getenv("NTFY_TOPIC"):
        merged["notifications"]["ntfy_topic"] = os.environ["NTFY_TOPIC"]
    if os.getenv("OLLAMA_HOST"):
        merged["llm"]["host"] = os.environ["OLLAMA_HOST"]
    return merged


CONFIG: dict[str, Any] = load_config()


def get(path: str, default: Any = None) -> Any:
    """Fetch a nested config value with a dotted path, e.g. get('llm.model')."""
    node: Any = CONFIG
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node
