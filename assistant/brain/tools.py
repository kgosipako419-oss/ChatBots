"""A small tool registry. Skills register Python functions plus a JSON schema;
the LLM sees the schemas and the dispatcher runs the functions.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]          # JSON schema for the function arguments
    func: Callable[..., Any]
    dangerous: bool = False             # requires user confirmation before running

    def to_ollama(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class Registry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        self.tools[tool.name] = tool

    def schemas(self) -> list[dict[str, Any]]:
        return [t.to_ollama() for t in self.tools.values()]

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        """Run a tool and return a string result for the LLM to read."""
        tool = self.tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'."
        try:
            # Only pass arguments the function actually accepts.
            sig = inspect.signature(tool.func)
            accepted = {k: v for k, v in (arguments or {}).items() if k in sig.parameters}
            result = tool.func(**accepted)
            return str(result) if result is not None else "Done."
        except Exception as exc:  # surface errors back to the model, don't crash the loop
            return f"Error running {name}: {exc}"


# Global registry shared across skills.
REGISTRY = Registry()


def tool(
    name: str,
    description: str,
    parameters: dict[str, Any] | None = None,
    dangerous: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: register a function as an LLM-callable tool.

    `parameters` is a JSON-schema object describing the arguments. If omitted,
    the tool takes no arguments.
    """
    schema = parameters or {"type": "object", "properties": {}}

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        REGISTRY.register(
            Tool(name=name, description=description, parameters=schema,
                 func=func, dangerous=dangerous)
        )
        return func

    return decorator
