"""Model usage, cost, and consumption intelligence for AHMED AI OS.

B40 deliberately keeps pricing vendor-neutral. Costs are estimates derived from
configured token prices; missing pricing never becomes a fabricated cost.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Protocol
from uuid import UUID, uuid4

from core.models.contracts import ModelTask


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Configurable token pricing expressed in USD per one million tokens."""

    provider: str
    model: str
    input_per_1m_tokens: float
    output_per_1m_tokens: float

    def __post_init__(self) -> None:
        if not self.provider:
            raise ValueError("pricing provider is required")
        if not self.model:
            raise ValueError("pricing model is required")
        if self.input_per_1m_tokens < 0 or self.output_per_1m_tokens < 0:
            raise ValueError("pricing values must be >= 0")


class ModelPricingCatalog:
    """In-memory pricing catalog with exact and wildcard provider/model matching."""

    def __init__(self, prices: Iterable[ModelPricing] = ()) -> None:
        self._prices: dict[tuple[str, str], ModelPricing] = {}
        for price in prices:
            self.register(price)

    def register(self, pricing: ModelPricing) -> None:
        self._prices[(pricing.provider, pricing.model)] = pricing

    def get(self, provider: str, model: str) -> ModelPricing | None:
        return (
            self._prices.get((provider, model))
            or self._prices.get((provider, "*"))
            or self._prices.get(("*", model))
            or self._prices.get(("*", "*"))
        )

    def estimate(
        self,
        *,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float | None:
        pricing = self.get(provider, model)
        if pricing is None:
            return None
        return (
            (max(prompt_tokens, 0) / 1_000_000) * pricing.input_per_1m_tokens
            + (max(completion_tokens, 0) / 1_000_000) * pricing.output_per_1m_tokens
        )

    @classmethod
    def from_json(cls, raw: str) -> "ModelPricingCatalog":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("MODEL_PRICING_JSON must contain valid JSON") from exc
        if not isinstance(payload, list):
            raise ValueError("MODEL_PRICING_JSON must be a JSON list")

        prices: list[ModelPricing] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("each pricing entry must be a JSON object")
            try:
                prices.append(
                    ModelPricing(
                        provider=str(item["provider"]),
                        model=str(item["model"]),
                        input_per_1m_tokens=float(item["input_per_1m_tokens"]),
                        output_per_1m_tokens=float(item["output_per_1m_tokens"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid pricing entry in MODEL_PRICING_JSON") from exc
        return cls(prices)

    def to_list(self) -> list[dict[str, object]]:
        return [asdict(price) for price in self._prices.values()]


@dataclass(frozen=True, slots=True)
class ModelUsageRecord:
    """One provider attempt, including successful, failed, retry, and fallback attempts."""

    request_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utc_now)
    task: ModelTask = ModelTask.CHAT
    provider: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tokens_available: bool = False
    latency_ms: float = 0.0
    success: bool = True
    fallback_used: bool = False
    attempt: int = 1
    estimated_cost_usd: float | None = None
    error: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0 or self.completion_tokens < 0 or self.total_tokens < 0:
            raise ValueError("token counts must be >= 0")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")
        if self.attempt < 1:
            raise ValueError("attempt must be >= 1")


@dataclass(frozen=True, slots=True)
class ModelUsageAggregate:
    """Aggregated usage intelligence for a provider, model, task, or the whole runtime."""

    attempts: int = 0
    requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    fallback_requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    requests_with_token_usage: int = 0
    estimated_cost_usd: float = 0.0
    priced_attempts: int = 0
    total_latency_ms: float = 0.0

    @property
    def error_rate(self) -> float:
        return self.failed_requests / self.requests if self.requests else 0.0

    @property
    def fallback_rate(self) -> float:
        return self.fallback_requests / self.requests if self.requests else 0.0

    @property
    def average_latency_ms(self) -> float:
        return self.total_latency_ms / self.attempts if self.attempts else 0.0


class ModelUsageStore(Protocol):
    def record(self, usage: ModelUsageRecord) -> None: ...

    def records(self) -> tuple[ModelUsageRecord, ...]: ...


class InMemoryModelUsageStore(ModelUsageStore):
    def __init__(self) -> None:
        self._records: list[ModelUsageRecord] = []

    def record(self, usage: ModelUsageRecord) -> None:
        self._records.append(usage)

    def records(self) -> tuple[ModelUsageRecord, ...]:
        return tuple(self._records)


class JsonFileModelUsageStore(ModelUsageStore):
    """Simple durable JSON store suitable for one application process."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._records: list[ModelUsageRecord] = self._load()

    def record(self, usage: ModelUsageRecord) -> None:
        self._records.append(usage)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([self._serialize(item) for item in self._records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def records(self) -> tuple[ModelUsageRecord, ...]:
        return tuple(self._records)

    def _load(self) -> list[ModelUsageRecord]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid model usage store: {self.path}") from exc
        if not isinstance(payload, list):
            raise ValueError(f"model usage store must be a JSON list: {self.path}")
        return [self._deserialize(item) for item in payload]

    @staticmethod
    def _serialize(record: ModelUsageRecord) -> dict[str, object]:
        payload = asdict(record)
        payload["request_id"] = str(record.request_id)
        payload["occurred_at"] = record.occurred_at.isoformat()
        payload["task"] = record.task.value
        return payload

    @staticmethod
    def _deserialize(payload: object) -> ModelUsageRecord:
        if not isinstance(payload, dict):
            raise ValueError("model usage records must be JSON objects")
        try:
            return ModelUsageRecord(
                request_id=UUID(str(payload["request_id"])),
                occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
                task=ModelTask(str(payload["task"])),
                provider=str(payload["provider"]),
                model=str(payload["model"]),
                prompt_tokens=int(payload.get("prompt_tokens", 0)),
                completion_tokens=int(payload.get("completion_tokens", 0)),
                total_tokens=int(payload.get("total_tokens", 0)),
                tokens_available=bool(payload.get("tokens_available", False)),
                latency_ms=float(payload.get("latency_ms", 0.0)),
                success=bool(payload.get("success", False)),
                fallback_used=bool(payload.get("fallback_used", False)),
                attempt=int(payload.get("attempt", 1)),
                estimated_cost_usd=(
                    None
                    if payload.get("estimated_cost_usd") is None
                    else float(payload["estimated_cost_usd"])
                ),
                error=None if payload.get("error") is None else str(payload["error"]),
                metadata=dict(payload.get("metadata", {})),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid model usage record") from exc


def _aggregate(records: Iterable[ModelUsageRecord]) -> ModelUsageAggregate:
    items = tuple(records)
    if not items:
        return ModelUsageAggregate()

    by_request: dict[UUID, list[ModelUsageRecord]] = defaultdict(list)
    for item in items:
        by_request[item.request_id].append(item)

    successful_requests = sum(1 for attempts in by_request.values() if any(item.success for item in attempts))
    failed_requests = sum(1 for attempts in by_request.values() if not any(item.success for item in attempts))
    fallback_requests = sum(
        1 for attempts in by_request.values() if any(item.fallback_used for item in attempts)
    )
    return ModelUsageAggregate(
        attempts=len(items),
        requests=len(by_request),
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        successful_attempts=sum(item.success for item in items),
        failed_attempts=sum(not item.success for item in items),
        fallback_requests=fallback_requests,
        prompt_tokens=sum(item.prompt_tokens for item in items),
        completion_tokens=sum(item.completion_tokens for item in items),
        total_tokens=sum(item.total_tokens for item in items),
        requests_with_token_usage=len({item.request_id for item in items if item.tokens_available}),
        estimated_cost_usd=sum(item.estimated_cost_usd or 0.0 for item in items),
        priced_attempts=sum(item.estimated_cost_usd is not None for item in items),
        total_latency_ms=sum(item.latency_ms for item in items),
    )


def summarize_usage(records: Iterable[ModelUsageRecord]) -> ModelUsageAggregate:
    return _aggregate(records)


def group_usage(
    records: Iterable[ModelUsageRecord],
    *,
    dimension: str,
) -> dict[str, ModelUsageAggregate]:
    valid_dimensions = {"provider", "model", "task"}
    if dimension not in valid_dimensions:
        raise ValueError(f"unsupported usage dimension: {dimension}")

    groups: dict[str, list[ModelUsageRecord]] = defaultdict(list)
    for item in records:
        value = item.task.value if dimension == "task" else str(getattr(item, dimension))
        groups[value].append(item)
    return {key: _aggregate(value) for key, value in sorted(groups.items())}
