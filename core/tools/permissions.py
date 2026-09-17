"""Tool-level permission gate."""

from __future__ import annotations

from core.domain.models import ActionLevel
from core.tools.models import ToolSpec


class ToolPermissionPolicy:
    """Explicit allow-list policy; execution is denied unless authorized."""

    def __init__(self, allowed_tools: set[str] | None = None) -> None:
        self.allowed_tools = allowed_tools or set()

    def authorize(self, spec: ToolSpec, approved: bool = False) -> bool:
        if spec.name not in self.allowed_tools:
            return False
        if spec.action_level == ActionLevel.EXECUTE and not approved:
            return False
        return True
