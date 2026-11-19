"""mcp_client.py — consume the MCP ecosystem (120k+ servers) behind Janus rings.

Minimal stdio JSON-RPC client (MCP 2024-11-05): initialize -> tools/list ->
tools/call. Discovered tools register into tools.TOOLS as `mcp_<server>_<tool>`
at the WRITE ring (receipt-logged); world-acting use still needs the kernel's
preview discipline at call sites. Config: JANUS_MCP_SERVERS as JSON list of
{"name": ..., "command": [...]} — e.g. the official filesystem/fetch servers.
"""
from __future__ import annotations

import json
import os
import subprocess


class McpServer:
    def __init__(self, name: str, command: list[str]):
        self.name = name
        self.proc = subprocess.Popen(command, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, text=True)
        self._id = 0
        self._rpc("initialize", {"protocolVersion": "2024-11-05",
                                 "capabilities": {}, "clientInfo": {"name": "janus-v2", "version": "2.0"}})
        self._notify("notifications/initialized", {})

    def _send(self, payload: dict) -> None:
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def _rpc(self, method: str, params: dict) -> dict:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"MCP server {self.name} closed")
            msg = json.loads(line)
            if msg.get("id") == self._id:
                return msg.get("result", {})

    def _notify(self, method: str, params: dict) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def list_tools(self) -> list[dict]:
        return self._rpc("tools/list", {}).get("tools", [])

    def call(self, tool: str, arguments: dict) -> dict:
        return self._rpc("tools/call", {"name": tool, "arguments": arguments})

    def close(self) -> None:
        try:
            self.proc.terminate()
        except Exception:
            pass


def configured_servers() -> list[dict]:
    try:
        return json.loads(os.environ.get("JANUS_MCP_SERVERS", "[]"))
    except Exception:
        return []


def register_all() -> list[str]:
    """Discover tools from every configured MCP server into TOOLS (write ring)."""
    from janus_v2 import tools as _tools
    registered = []
    for cfg in configured_servers():
        server = McpServer(cfg["name"], cfg["command"])
        for tool in server.list_tools():
            key = f"mcp_{cfg['name']}_{tool['name']}"
            _tools.TOOLS[key] = (
                (lambda s, t: lambda **kw: s.call(t, kw))(server, tool["name"]),
                _tools.RING_WRITE)
            registered.append(key)
    return registered
