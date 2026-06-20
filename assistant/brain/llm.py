"""Ollama chat client with a tool-calling loop.

Sends the conversation plus tool schemas to a local Ollama model. If the model
asks to call tools, we run them, feed the results back, and repeat until the
model produces a final spoken reply.
"""
from __future__ import annotations

import json
from typing import Any, Callable

import requests

from .. import config
from .tools import REGISTRY

SYSTEM_PROMPT = """You are {name}, a local voice assistant running on the user's Windows PC.
You control the computer and connected devices by calling tools. Your replies are
spoken aloud, so keep them to ONE short sentence — natural and conversational, no
lists or markdown. Don't over-explain or offer extra options unless asked.

Rules:
- Use tools to actually perform actions. Do not claim you did something unless a tool did it.
- For destructive actions (shutdown, restart, running remote commands), briefly confirm
  intent in your wording; the system will also ask the user to confirm.
- After tools run, give a one-sentence spoken summary of what happened.
- If a request is ambiguous, ask a brief clarifying question instead of guessing.
- Do not read out raw URLs, file paths, or JSON unless asked.
"""

# Type for a callback that asks the user to confirm a dangerous action.
ConfirmFn = Callable[[str], bool]


class Brain:
    def __init__(self, confirm_fn: ConfirmFn | None = None) -> None:
        self.host = config.get("llm.host").rstrip("/")
        self.model = config.get("llm.model")
        self.temperature = config.get("llm.temperature", 0.3)
        self.num_ctx = config.get("llm.num_ctx", 4096)
        self.timeout = config.get("llm.timeout", 300)
        self.keep_alive = config.get("llm.keep_alive", "30m")
        self.require_confirm = config.get("assistant.require_confirmation_for_dangerous", True)
        self.confirm_fn = confirm_fn or (lambda _msg: True)
        name = config.get("assistant.name", "Computer")
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT.format(name=name)}
        ]

    def _chat(self, use_tools: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self.messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }
        if use_tools:
            payload["tools"] = REGISTRY.schemas()
        resp = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()["message"]

    def warm_up(self) -> None:
        """Preload the model into memory so the first real command isn't slow."""
        try:
            requests.post(
                f"{self.host}/api/generate",
                json={"model": self.model, "prompt": "ok", "stream": False,
                      "keep_alive": self.keep_alive},
                timeout=self.timeout,
            )
        except Exception:
            pass

    def ask(self, user_text: str, max_tool_rounds: int = 5) -> str:
        """Process one user utterance; return the assistant's spoken reply."""
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(max_tool_rounds):
            message = self._chat(use_tools=True)
            self.messages.append(message)
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                return (message.get("content") or "").strip()

            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", {}) or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}

                result = self._run_tool(name, args)
                self.messages.append({"role": "tool", "name": name, "content": result})

        # Ran out of tool rounds — ask the model to wrap up without more tools.
        final = self._chat(use_tools=False)
        self.messages.append(final)
        return (final.get("content") or "").strip()

    def _run_tool(self, name: str, args: dict[str, Any]) -> str:
        tool = REGISTRY.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'."
        if tool.dangerous and self.require_confirm:
            summary = f"{name} with {args}" if args else name
            if not self.confirm_fn(summary):
                return "The user declined this action."
        return REGISTRY.dispatch(name, args)


def check_ollama() -> tuple[bool, str]:
    """Return (ok, message) describing whether Ollama and the model are reachable."""
    host = config.get("llm.host").rstrip("/")
    model = config.get("llm.model")
    try:
        resp = requests.get(f"{host}/api/tags", timeout=5)
        resp.raise_for_status()
    except Exception as exc:
        return False, f"Cannot reach Ollama at {host} ({exc}). Is `ollama serve` running?"
    installed = [m.get("name", "") for m in resp.json().get("models", [])]
    if not any(m == model or m.startswith(model.split(":")[0]) for m in installed):
        return False, (
            f"Model '{model}' not found. Installed: {installed or 'none'}. "
            f"Run:  ollama pull {model}"
        )
    return True, f"Ollama OK - using model '{model}'."
