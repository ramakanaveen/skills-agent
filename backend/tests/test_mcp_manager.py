"""
Tests for mcp_manager.py

Covers:
  - StdioMcpClient: connect, list_tools, call_tool, disconnect
  - HttpMcpClient: connect, list_tools, call_tool
  - _extract_result: text content, error, empty
  - McpManager: startup with no servers, graceful degradation,
    tool registration, rate limiting
"""

import json
import subprocess
from io import StringIO
from unittest.mock import MagicMock, patch, call

import httpx
import pytest

from mcp_manager import (
    StdioMcpClient,
    HttpMcpClient,
    McpManager,
    _extract_result,
)
from tool_registry import ToolRegistry


# ── _extract_result ────────────────────────────────────────────────────────────

class TestExtractResult:
    def test_extracts_text_content(self):
        resp = {"result": {"content": [{"type": "text", "text": "hello"}]}}
        assert _extract_result(resp) == "hello"

    def test_joins_multiple_text_blocks(self):
        resp = {"result": {"content": [
            {"type": "text", "text": "line1"},
            {"type": "text", "text": "line2"},
        ]}}
        assert _extract_result(resp) == "line1\nline2"

    def test_skips_non_text_content(self):
        resp = {"result": {"content": [
            {"type": "image", "data": "..."},
            {"type": "text", "text": "visible"},
        ]}}
        assert _extract_result(resp) == "visible"

    def test_returns_json_when_no_text_content(self):
        resp = {"result": {"something": "else"}}
        result = _extract_result(resp)
        assert "something" in result

    def test_returns_error_message(self):
        resp = {"error": {"code": -32601, "message": "Method not found"}}
        result = _extract_result(resp)
        assert "ERROR" in result
        assert "Method not found" in result

    def test_error_with_missing_message(self):
        resp = {"error": {}}
        result = _extract_result(resp)
        assert "ERROR" in result


# ── StdioMcpClient ─────────────────────────────────────────────────────────────

def _make_stdio_proc(*responses):
    """Return a mock Popen where stdout.readline() yields the given JSON dicts."""
    lines = [json.dumps(r) + "\n" for r in responses]
    proc = MagicMock()
    proc.stdin = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.readline.side_effect = lines
    return proc


class TestStdioMcpClient:
    def _init_responses(self):
        """Responses for initialize (id=1) and initialized notification (no response needed)."""
        return [{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}]

    def test_connect_sends_initialize(self):
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        proc = _make_stdio_proc(init_resp)

        with patch("subprocess.Popen", return_value=proc):
            client = StdioMcpClient("test", "some-cmd", {})
            client.connect()

        written = "".join(call.args[0] for call in proc.stdin.write.call_args_list)
        assert "initialize" in written

    def test_list_tools_returns_tools(self):
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        list_resp = {"jsonrpc": "2.0", "id": 2, "result": {
            "tools": [{"name": "search", "description": "Search stuff",
                       "inputSchema": {"type": "object", "properties": {}}}]
        }}
        proc = _make_stdio_proc(init_resp, list_resp)

        with patch("subprocess.Popen", return_value=proc):
            client = StdioMcpClient("test", "cmd", {})
            client.connect()
            tools = client.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "search"

    def test_call_tool_returns_text(self):
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        call_resp = {"jsonrpc": "2.0", "id": 2, "result": {
            "content": [{"type": "text", "text": "search results here"}]
        }}
        proc = _make_stdio_proc(init_resp, call_resp)

        with patch("subprocess.Popen", return_value=proc):
            client = StdioMcpClient("test", "cmd", {})
            client.connect()
            result = client.call_tool("search", {"query": "hello"})

        assert result == "search results here"

    def test_env_vars_resolved_on_connect(self):
        import os
        os.environ["TEST_MCP_TOKEN"] = "secret123"
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        proc = _make_stdio_proc(init_resp)

        captured_env = {}

        def fake_popen(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            return proc

        with patch("subprocess.Popen", side_effect=fake_popen):
            client = StdioMcpClient("test", "cmd", {"MY_TOKEN": "${TEST_MCP_TOKEN}"})
            client.connect()

        assert captured_env.get("MY_TOKEN") == "secret123"

    def test_disconnect_closes_process(self):
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        proc = _make_stdio_proc(init_resp)

        with patch("subprocess.Popen", return_value=proc):
            client = StdioMcpClient("test", "cmd", {})
            client.connect()
            client.disconnect()

        proc.stdin.close.assert_called_once()
        proc.wait.assert_called_once()

    def test_skips_notification_lines_while_waiting_for_response(self):
        """Lines without an id (notifications) should be skipped."""
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        notification = {"jsonrpc": "2.0", "method": "some/notification", "params": {}}
        list_resp = {"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}
        proc = _make_stdio_proc(init_resp, notification, list_resp)

        with patch("subprocess.Popen", return_value=proc):
            client = StdioMcpClient("test", "cmd", {})
            client.connect()
            tools = client.list_tools()

        assert tools == []


# ── HttpMcpClient ──────────────────────────────────────────────────────────────

def _make_http_client(responses: list[dict]):
    """Return a mock httpx.Client that returns the given JSON responses in order."""
    mock_client = MagicMock()
    mock_responses = []
    for resp_data in responses:
        r = MagicMock()
        r.json.return_value = resp_data
        r.raise_for_status = MagicMock()
        mock_responses.append(r)
    mock_client.post.side_effect = mock_responses
    return mock_client


class TestHttpMcpClient:
    def test_connect_posts_initialize(self):
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        # initialized notification post returns anything
        notify_resp = MagicMock()
        notify_resp.raise_for_status = MagicMock()

        mock_client = _make_http_client([init_resp])
        mock_client.post.side_effect = [
            MagicMock(json=MagicMock(return_value=init_resp), raise_for_status=MagicMock()),
            MagicMock(raise_for_status=MagicMock()),  # notification
        ]

        with patch("httpx.Client", return_value=mock_client):
            client = HttpMcpClient("test", "http://localhost:3000", {})
            client.connect()

        first_call_body = mock_client.post.call_args_list[0].kwargs.get("json", {})
        assert first_call_body.get("method") == "initialize"

    def test_list_tools_returns_tools(self):
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        list_resp = {"jsonrpc": "2.0", "id": 2, "result": {
            "tools": [{"name": "get_page", "description": "Get a Confluence page",
                       "inputSchema": {"type": "object", "properties": {}}}]
        }}

        mock_client = MagicMock()
        mock_client.post.side_effect = [
            MagicMock(json=MagicMock(return_value=init_resp), raise_for_status=MagicMock()),
            MagicMock(raise_for_status=MagicMock()),  # notification
            MagicMock(json=MagicMock(return_value=list_resp), raise_for_status=MagicMock()),
        ]

        with patch("httpx.Client", return_value=mock_client):
            client = HttpMcpClient("test", "http://localhost:3000", {})
            client.connect()
            tools = client.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "get_page"

    def test_auth_headers_resolved_from_env(self):
        import os
        os.environ["CONF_TOKEN"] = "mytoken"
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}

        captured_headers = {}

        def fake_client(**kwargs):
            captured_headers.update(kwargs.get("headers", {}))
            c = MagicMock()
            c.post.return_value = MagicMock(
                json=MagicMock(return_value=init_resp),
                raise_for_status=MagicMock(),
            )
            return c

        with patch("httpx.Client", side_effect=fake_client):
            client = HttpMcpClient("test", "http://x", {"Authorization": "Bearer ${CONF_TOKEN}"})
            client.connect()

        assert captured_headers.get("Authorization") == "Bearer mytoken"

    def test_disconnect_closes_client(self):
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        mock_client = MagicMock()
        mock_client.post.return_value = MagicMock(
            json=MagicMock(return_value=init_resp),
            raise_for_status=MagicMock(),
        )

        with patch("httpx.Client", return_value=mock_client):
            client = HttpMcpClient("test", "http://x", {})
            client.connect()
            client.disconnect()

        mock_client.close.assert_called_once()


# ── McpManager ─────────────────────────────────────────────────────────────────

class TestMcpManager:
    def _fresh_registry(self):
        return ToolRegistry()

    def test_startup_with_no_servers_is_a_no_op(self):
        reg = self._fresh_registry()
        with patch("mcp_manager.cfg") as mock_cfg:
            mock_cfg.mcp_servers = []
            m = McpManager()
            m.startup(reg)
        assert reg.names() == []

    def test_startup_skips_disabled_server(self):
        reg = self._fresh_registry()
        with patch("mcp_manager.cfg") as mock_cfg:
            mock_cfg.mcp_servers = [{"name": "github", "transport": "http",
                                     "url": "http://x", "enabled": False}]
            m = McpManager()
            m.startup(reg)
        assert reg.names() == []

    def test_startup_graceful_degradation_on_connect_failure(self):
        reg = self._fresh_registry()
        with patch("mcp_manager.cfg") as mock_cfg:
            mock_cfg.mcp_servers = [{"name": "broken", "transport": "http",
                                     "url": "http://does-not-exist"}]
            with patch("httpx.Client") as mock_cls:
                mock_cls.return_value.post.side_effect = httpx.ConnectError("refused")
                m = McpManager()
                m.startup(reg)  # must not raise

        assert reg.names() == []
        assert m.connected_servers() == []

    def test_startup_registers_tools_from_server(self):
        reg = self._fresh_registry()
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        list_resp = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [
            {"name": "search_code", "description": "Search code",
             "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
            {"name": "create_issue", "description": "Create issue",
             "inputSchema": {"type": "object", "properties": {}, "required": []}},
        ]}}

        mock_client = MagicMock()
        mock_client.post.side_effect = [
            MagicMock(json=MagicMock(return_value=init_resp), raise_for_status=MagicMock()),
            MagicMock(raise_for_status=MagicMock()),  # notification
            MagicMock(json=MagicMock(return_value=list_resp), raise_for_status=MagicMock()),
        ]

        with patch("mcp_manager.cfg") as mock_cfg, patch("httpx.Client", return_value=mock_client):
            mock_cfg.mcp_servers = [{"name": "github", "transport": "http",
                                     "url": "http://mcp-github"}]
            m = McpManager()
            m.startup(reg)

        assert "github__search_code" in reg.names()
        assert "github__create_issue" in reg.names()
        assert m.connected_servers() == ["github"]

    def test_tool_schema_prefixed_with_server_name(self):
        reg = self._fresh_registry()
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        list_resp = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [
            {"name": "get_page", "description": "Get a page",
             "inputSchema": {"type": "object", "properties": {}}}
        ]}}

        mock_client = MagicMock()
        mock_client.post.side_effect = [
            MagicMock(json=MagicMock(return_value=init_resp), raise_for_status=MagicMock()),
            MagicMock(raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=list_resp), raise_for_status=MagicMock()),
        ]

        with patch("mcp_manager.cfg") as mock_cfg, patch("httpx.Client", return_value=mock_client):
            mock_cfg.mcp_servers = [{"name": "confluence", "transport": "http",
                                     "url": "http://mcp-conf"}]
            m = McpManager()
            m.startup(reg)

        schemas = {s["name"]: s for s in reg.schemas()}
        assert "confluence__get_page" in schemas
        assert "[confluence]" in schemas["confluence__get_page"]["description"]

    def test_rate_limiting_blocks_excess_calls(self):
        reg = self._fresh_registry()
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        list_resp = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [
            {"name": "search", "description": "Search",
             "inputSchema": {"type": "object", "properties": {}}}
        ]}}
        call_resp = {"jsonrpc": "2.0", "id": 3, "result": {
            "content": [{"type": "text", "text": "results"}]
        }}

        mock_client = MagicMock()
        mock_client.post.side_effect = [
            MagicMock(json=MagicMock(return_value=init_resp), raise_for_status=MagicMock()),
            MagicMock(raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=list_resp), raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=call_resp), raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=call_resp), raise_for_status=MagicMock()),
        ]

        with patch("mcp_manager.cfg") as mock_cfg, patch("httpx.Client", return_value=mock_client):
            mock_cfg.mcp_servers = [{"name": "svc", "transport": "http",
                                     "url": "http://x", "rate_limit": 2}]
            m = McpManager()
            m.startup(reg)

        # First two calls succeed
        r1 = reg.execute("svc__search", {}, session_id="sess1")
        r2 = reg.execute("svc__search", {}, session_id="sess1")
        # Third call in same session is blocked
        r3 = reg.execute("svc__search", {}, session_id="sess1")

        assert r1 == "results"
        assert r2 == "results"
        assert "Rate limit" in r3

    def test_rate_limit_is_per_session(self):
        """Different sessions have independent call budgets."""
        reg = self._fresh_registry()
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        list_resp = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [
            {"name": "search", "description": "s",
             "inputSchema": {"type": "object", "properties": {}}}
        ]}}
        call_resp = {"jsonrpc": "2.0", "id": 3, "result": {
            "content": [{"type": "text", "text": "ok"}]
        }}

        mock_client = MagicMock()
        mock_client.post.side_effect = [
            MagicMock(json=MagicMock(return_value=init_resp), raise_for_status=MagicMock()),
            MagicMock(raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=list_resp), raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=call_resp), raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=call_resp), raise_for_status=MagicMock()),
        ]

        with patch("mcp_manager.cfg") as mock_cfg, patch("httpx.Client", return_value=mock_client):
            mock_cfg.mcp_servers = [{"name": "svc", "transport": "http",
                                     "url": "http://x", "rate_limit": 1}]
            m = McpManager()
            m.startup(reg)

        r1 = reg.execute("svc__search", {}, session_id="sess-a")
        r2 = reg.execute("svc__search", {}, session_id="sess-b")  # fresh budget

        assert r1 == "ok"
        assert r2 == "ok"

    def test_shutdown_disconnects_all_clients(self):
        reg = self._fresh_registry()
        init_resp = {"jsonrpc": "2.0", "id": 1, "result": {}}
        list_resp = {"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}

        mock_client = MagicMock()
        mock_client.post.side_effect = [
            MagicMock(json=MagicMock(return_value=init_resp), raise_for_status=MagicMock()),
            MagicMock(raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=list_resp), raise_for_status=MagicMock()),
        ]

        with patch("mcp_manager.cfg") as mock_cfg, patch("httpx.Client", return_value=mock_client):
            mock_cfg.mcp_servers = [{"name": "svc", "transport": "http", "url": "http://x"}]
            m = McpManager()
            m.startup(reg)
            m.shutdown()

        mock_client.close.assert_called_once()
        assert m.connected_servers() == []
