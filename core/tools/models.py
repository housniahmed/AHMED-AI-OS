"""Tool contracts and execution records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import UUID, uuid4

from core.domain.models import ActionLevel


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    action_level: ActionLevel
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class ToolCall:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class ToolResult:
    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None
    call_id: UUID | None = None
