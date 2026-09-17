"""Provider-neutral LLM contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModelTask(str, Enum):
    CHAT = "chat"
    REASONING = "reasoning"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"


@dataclass(frozen=True, slots=True)
class ModelRequest:
    task: ModelTask
    messages: tuple[dict[str, str], ...] = ()
    input_text: str = ""
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelResponse:
    text: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
