"""Tool discovery and registration without vendor coupling."""

from __future__ import annotations

from core.tools.models import ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if not spec.name.strip():
            raise ValueError("tool name cannot be empty")
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def list(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools.values())

    def discover(self, *, tags: tuple[str, ...] = (), level=None) -> tuple[ToolSpec, ...]:
        return tuple(
            spec for spec in self._tools.values()
            if (not tags or any(tag in spec.tags for tag in tags))
            and (level is None or spec.action_level == level)
        )
