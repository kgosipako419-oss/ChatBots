"""Control other computers on your network over SSH.

Configure machines in config.yaml under remote_hosts. Key-based auth is strongly
preferred over storing passwords. Running remote commands is a dangerous tool, so
it asks for confirmation by default.
"""
from __future__ import annotations

from pathlib import Path

from .. import config
from ..brain.tools import tool

try:
    import paramiko
    _HAS_PARAMIKO = True
except Exception:  # pragma: no cover
    _HAS_PARAMIKO = False


@tool(
    "list_remote_hosts",
    "List the other computers that are configured and can be controlled over the network.",
    {"type": "object", "properties": {}},
)
def list_remote_hosts() -> str:
    hosts = config.get("remote_hosts", {}) or {}
    if not hosts:
        return "No remote computers are configured yet."
    return "Configured computers: " + ", ".join(hosts.keys()) + "."


@tool(
    "run_remote_command",
    "Run a shell command on another configured computer over SSH and return its output.",
    {
        "type": "object",
        "properties": {
            "host_name": {"type": "string", "description": "Name of the host from the config"},
            "command": {"type": "string", "description": "Shell command to execute remotely"},
        },
        "required": ["host_name", "command"],
    },
    dangerous=True,
)
def run_remote_command(host_name: str, command: str) -> str:
    if not _HAS_PARAMIKO:
        return "Remote control needs the paramiko package (pip install paramiko)."
    hosts = config.get("remote_hosts", {}) or {}
    spec = hosts.get(host_name)
    if spec is None:
        return f"Unknown host '{host_name}'. Configured: {', '.join(hosts) or 'none'}."

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs: dict = {
            "hostname": spec["host"],
            "username": spec.get("user"),
            "port": spec.get("port", 22),
            "timeout": 10,
        }
        if spec.get("password"):
            connect_kwargs["password"] = spec["password"]
        if spec.get("key_path"):
            connect_kwargs["key_filename"] = str(Path(spec["key_path"]).expanduser())
        client.connect(**connect_kwargs)

        _stdin, stdout, stderr = client.exec_command(command, timeout=30)
        out = stdout.read().decode("utf-8", "replace").strip()
        err = stderr.read().decode("utf-8", "replace").strip()
        if err and not out:
            return f"{host_name} error: {err}"
        result = out or "Command ran with no output."
        return f"{host_name}: {result}"
    except Exception as exc:
        return f"Could not run command on {host_name}: {exc}"
    finally:
        client.close()
