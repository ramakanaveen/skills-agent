"""
Tool Registry — central registry for all agent tools.

Built-in tools register themselves when tool_executor is imported.
MCP tools register themselves when mcp_manager connects at startup.

Both tool types are identical from the perspective of the agentic loop:
  - execute() routes by name
  - schemas() feeds tool definitions to the Anthropic API

Usage:
    from tool_registry import registry

    # Register a tool (done once at module load / server startup)
    registry.register("my_tool", handler_fn, schema_dict)

    # Execute a tool call from the agentic loop
    result = registry.execute("my_tool", input_data,
                              session_id=sid, anthropic_client=client)

    # Get all tool definitions for the API (context_assembler)
    tools = registry.schemas()

    # Get schemas excluding specific tools (e.g. for subagents)
    tools = registry.schemas(exclude={"spawn_agent"})
"""

from __future__ import annotations

from typing import Callable


class ToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = {}
        self._schemas: dict[str, dict] = {}

    def register(self, name: str, handler: Callable, schema: dict) -> None:
        """Register a tool handler and its API schema under the given name."""
        self._handlers[name] = handler
        self._schemas[name] = schema

    def execute(self, name: str, input_data: dict, **ctx) -> str:
        """
        Route a tool call to its handler.

        ctx kwargs are forwarded to the handler. Built-in tools use:
          session_id      - for output path scoping
          anthropic_client - for analyze_file / spawn_agent API calls

        Returns a string result (or error message prefixed with ERROR:).
        """
        if name not in self._handlers:
            return f"ERROR: Unknown tool: {name}"
        return self._handlers[name](input_data, **ctx)

    def schemas(self, exclude: set[str] | None = None) -> list[dict]:
        """Return tool definition dicts suitable for the Anthropic tools= param."""
        excluded = exclude or set()
        return [s for n, s in self._schemas.items() if n not in excluded]

    def names(self) -> list[str]:
        """Return all registered tool names."""
        return list(self._handlers.keys())

    def is_registered(self, name: str) -> bool:
        return name in self._handlers


# Module-level singleton — import this everywhere
registry = ToolRegistry()
