"""
MCP Manager — connects to configured MCP servers at startup, discovers
their tools, and registers them into the tool registry.

MCP tools are first-class tools: Claude sees them alongside built-in
tools and calls them by name. The agentic loop routes them here
transparently via the registry.

Transports supported:
  stdio — spawn a local process; JSON-RPC over stdin/stdout
  http  — POST JSON-RPC to a running HTTP server (sync, httpx)

Security:
  - Only servers listed in config.yaml are ever reachable (allowlist)
  - Auth tokens resolved from environment, never stored in sessions
  - Rate limiting: max calls per (session, server) pair
  - Failed servers are skipped; the app always starts cleanly
  - MCP results are opaque strings — treated as untrusted external data

Tool naming: "{server_name}__{tool_name}"
  e.g. github__create_issue, confluence__search_pages
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
from typing import TYPE_CHECKING

import httpx

from config import cfg

if TYPE_CHECKING:
    from tool_registry import ToolRegistry

log = logging.getLogger(__name__)


# ── Transport clients ──────────────────────────────────────────────────────────

class StdioMcpClient:
    """MCP client over stdio — spawns a local process and speaks JSON-RPC."""

    def __init__(self, name: str, command: str, env: dict[str, str]) -> None:
        self._name = name
        self._command = command
        self._env = env
        self._proc: subprocess.Popen | None = None
        self._req_id = 0

    def connect(self) -> None:
        resolved = {k: os.path.expandvars(v) for k, v in self._env.items()}
        full_env = {**os.environ, **resolved}
        self._proc = subprocess.Popen(
            shlex.split(self._command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=full_env,
            text=True,
        )
        self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "skills-agent", "version": "1.0"},
        })
        self._notify("notifications/initialized", {})

    def list_tools(self) -> list[dict]:
        resp = self._rpc("tools/list", {})
        return resp.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        resp = self._rpc("tools/call", {"name": tool_name, "arguments": arguments})
        return _extract_result(resp)

    def disconnect(self) -> None:
        if self._proc:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
            self._proc = None

    # ── internal ──────────────────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _rpc(self, method: str, params: dict) -> dict:
        req_id = self._next_id()
        msg = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        self._proc.stdin.write(msg + "\n")
        self._proc.stdin.flush()
        # Read lines until we get the response matching our request id.
        # Notifications (no "id") are silently discarded.
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError(f"MCP server '{self._name}' closed stdout unexpectedly")
            try:
                resp = json.loads(line)
            except json.JSONDecodeError:
                continue
            if resp.get("id") == req_id:
                return resp

    def _notify(self, method: str, params: dict) -> None:
        msg = json.dumps({"jsonrpc": "2.0", "method": method, "params": params})
        self._proc.stdin.write(msg + "\n")
        self._proc.stdin.flush()


class HttpMcpClient:
    """MCP client over HTTP — sends JSON-RPC POST requests synchronously."""

    def __init__(self, name: str, url: str, headers: dict[str, str]) -> None:
        self._name = name
        self._url = url
        self._headers = headers
        self._client: httpx.Client | None = None
        self._req_id = 0

    def connect(self) -> None:
        resolved = {k: os.path.expandvars(v) for k, v in self._headers.items()}
        self._client = httpx.Client(
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **resolved,
            },
            timeout=30.0,
        )
        self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "skills-agent", "version": "1.0"},
        })
        self._notify("notifications/initialized", {})

    def list_tools(self) -> list[dict]:
        resp = self._rpc("tools/list", {})
        return resp.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        resp = self._rpc("tools/call", {"name": tool_name, "arguments": arguments})
        return _extract_result(resp)

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    # ── internal ──────────────────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _rpc(self, method: str, params: dict) -> dict:
        req_id = self._next_id()
        body = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        resp = self._client.post(self._url, json=body)
        resp.raise_for_status()
        return resp.json()

    def _notify(self, method: str, params: dict) -> None:
        body = {"jsonrpc": "2.0", "method": method, "params": params}
        try:
            self._client.post(self._url, json=body)
        except Exception:
            pass  # notifications are fire-and-forget


# ── Result extraction ──────────────────────────────────────────────────────────

def _extract_result(resp: dict) -> str:
    """Extract a plain-text result from a JSON-RPC tools/call response."""
    if "error" in resp:
        err = resp["error"]
        return f"ERROR: [{err.get('code', '?')}] {err.get('message', 'Unknown MCP error')}"
    result = resp.get("result", {})
    content = result.get("content", [])
    parts = [item.get("text", "") for item in content if item.get("type") == "text"]
    return "\n".join(parts) if parts else json.dumps(result)


# ── Manager ────────────────────────────────────────────────────────────────────

class McpManager:
    """
    Manages lifecycle and routing for all configured MCP servers.

    Call startup(registry) once from the FastAPI lifespan to connect all
    servers and register their tools. Call shutdown() to clean up.
    """

    def __init__(self) -> None:
        self._clients: dict[str, StdioMcpClient | HttpMcpClient] = {}
        self._rate_limits: dict[str, int] = {}
        # Track call counts per (session_id, server_name) for rate limiting
        self._call_counts: dict[tuple[str, str], int] = {}

    def startup(self, registry: ToolRegistry) -> None:
        """Connect to all enabled MCP servers and register their tools."""
        servers = cfg.mcp_servers
        if not servers:
            log.info("MCP: no servers configured")
            return

        for server_cfg in servers:
            if not server_cfg.get("enabled", True):
                log.info("MCP: server '%s' is disabled — skipped", server_cfg.get("name", "?"))
                continue
            self._connect_server(registry, server_cfg)

    def shutdown(self) -> None:
        """Disconnect all MCP server processes/connections."""
        for name, client in self._clients.items():
            try:
                client.disconnect()
                log.info("MCP: disconnected from '%s'", name)
            except Exception as exc:
                log.warning("MCP: error disconnecting '%s': %s", name, exc)
        self._clients.clear()

    def connected_servers(self) -> list[str]:
        return list(self._clients.keys())

    # ── internal ──────────────────────────────────────────────────────────────

    def _connect_server(self, registry: ToolRegistry, server_cfg: dict) -> None:
        name = server_cfg.get("name", "unknown")
        transport = server_cfg.get("transport", "http")
        rate_limit = int(server_cfg.get("rate_limit", 50))

        try:
            client = self._build_client(name, transport, server_cfg)
            client.connect()
            tools = client.list_tools()
        except Exception as exc:
            log.warning(
                "MCP: failed to connect to '%s' (%s) — skipping. Error: %s",
                name, transport, exc,
            )
            return

        self._clients[name] = client
        self._rate_limits[name] = rate_limit

        for tool_spec in tools:
            self._register_tool(registry, name, tool_spec, client, rate_limit)

        log.info("MCP: connected to '%s' via %s, registered %d tool(s)", name, transport, len(tools))

    def _build_client(
        self, name: str, transport: str, cfg: dict
    ) -> StdioMcpClient | HttpMcpClient:
        if transport == "stdio":
            return StdioMcpClient(
                name=name,
                command=cfg["command"],
                env=cfg.get("env", {}),
            )
        if transport == "http":
            return HttpMcpClient(
                name=name,
                url=cfg["url"],
                headers=cfg.get("headers", {}),
            )
        raise ValueError(f"Unsupported MCP transport: '{transport}'")

    def _register_tool(
        self,
        registry: ToolRegistry,
        server_name: str,
        tool_spec: dict,
        client: StdioMcpClient | HttpMcpClient,
        rate_limit: int,
    ) -> None:
        raw_name = tool_spec["name"]
        qualified_name = f"{server_name}__{raw_name}"

        # Capture variables explicitly to avoid closure/late-binding issues
        def make_handler(cl, rn, sn, rl):
            def handler(input_data: dict, **ctx) -> str:
                session_id = ctx.get("session_id") or "global"
                key = (session_id, sn)
                count = self._call_counts.get(key, 0)
                if count >= rl:
                    return (
                        f"ERROR: Rate limit exceeded for MCP server '{sn}' "
                        f"in this session ({rl} calls max)"
                    )
                self._call_counts[key] = count + 1
                try:
                    return cl.call_tool(rn, input_data)
                except Exception as exc:
                    return f"ERROR: MCP call failed for '{sn}/{rn}': {type(exc).__name__}: {exc}"
            return handler

        schema = {
            "name": qualified_name,
            "description": f"[{server_name}] {tool_spec.get('description', '')}",
            "input_schema": tool_spec.get(
                "inputSchema",
                {"type": "object", "properties": {}, "required": []},
            ),
        }
        registry.register(
            qualified_name,
            make_handler(client, raw_name, server_name, rate_limit),
            schema,
        )


# Module-level singleton
manager = McpManager()
