"""Provider reliability policies and persistent health state contracts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from time import sleep
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 2
    backoff_seconds: float = 0.25
    max_backoff_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff_seconds < 0 or self.max_backoff_seconds < 0:
            raise ValueError("backoff values must be >= 0")


@dataclass(frozen=True, slots=True)
class CircuitBreakerPolicy:
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")


@dataclass(slots=True)
class ProviderHealthState:
    enabled: bool = True
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    last_error: str | None = None
    circuit_open: bool = False
    opened_at: float | None = None
    last_success_at: float | None = None
    last_failure_at: float | None = None
    cooldown_until: float | None = None


class ProviderHealthStore(Protocol):
    def load(self, provider_name: str) -> ProviderHealthState | None: ...
    def save(self, provider_name: str, state: ProviderHealthState) -> None: ...


class InMemoryProviderHealthStore:
    def __init__(self) -> None:
        self._states: dict[str, ProviderHealthState] = {}
        self._lock = RLock()

    def load(self, provider_name: str) -> ProviderHealthState | None:
        with self._lock:
            state = self._states.get(provider_name)
            return None if state is None else ProviderHealthState(**asdict(state))

    def save(self, provider_name: str, state: ProviderHealthState) -> None:
        with self._lock:
            self._states[provider_name] = ProviderHealthState(**asdict(state))


class JsonFileProviderHealthStore:
    """Durable health store for a single-process deployment."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = RLock()

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def load(self, provider_name: str) -> ProviderHealthState | None:
        with self._lock:
            raw = self._read().get(provider_name)
            return ProviderHealthState(**raw) if isinstance(raw, dict) else None

    def save(self, provider_name: str, state: ProviderHealthState) -> None:
        with self._lock:
            data = self._read()
            data[provider_name] = asdict(state)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(self.path.suffix + ".tmp")
            temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            temp.replace(self.path)


def sleep_backoff(policy: RetryPolicy, attempt: int, *, sleeper=sleep) -> None:
    """Compatibility hook; router supplies its own sleep implementation."""
    delay = min(policy.backoff_seconds * (2 ** max(attempt - 1, 0)), policy.max_backoff_seconds)
    if delay > 0:
        sleeper(delay)
