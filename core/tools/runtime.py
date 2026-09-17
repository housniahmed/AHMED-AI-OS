"""Safe execution boundary for registered tools."""

from __future__ import annotations

from typing import Any, Callable

from core.tools.models import ToolCall, ToolResult
from core.tools.permissions import ToolPermissionPolicy
from core.tools.registry import ToolRegistry


class ToolRuntime:
    def __init__(self, registry: ToolRegistry, policy: ToolPermissionPolicy | None = None) -> None:
        self.registry = registry
        self.policy = policy or ToolPermissionPolicy()
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def bind(self, tool_name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self.registry.get(tool_name)
        if tool_name in self._handlers:
            raise ValueError(f"handler already bound: {tool_name}")
        self._handlers[tool_name] = handler

    def execute(self, call: ToolCall, *, approved: bool = False) -> ToolResult:
        try:
            spec = self.registry.get(call.tool_name)
            if not self.policy.authorize(spec, approved=approved):
                return ToolResult(call.tool_name, False, error="tool execution not authorized", call_id=call.id)
            handler = self._handlers.get(call.tool_name)
            if handler is None:
                return ToolResult(call.tool_name, False, error="tool handler not bound", call_id=call.id)
            output = handler(call.arguments)
            return ToolResult(call.tool_name, True, output=output, call_id=call.id)
        except Exception as exc:
            return ToolResult(call.tool_name, False, error=str(exc), call_id=call.id)
