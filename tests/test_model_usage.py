import tempfile
from pathlib import Path
from uuid import UUID

from core.models.contracts import ModelRequest, ModelResponse, ModelTask
from core.models.providers import ModelProvider
from core.models.router import ModelRoute, ModelRouter
from core.models.usage import (
    InMemoryModelUsageStore,
    JsonFileModelUsageStore,
    ModelPricing,
    ModelPricingCatalog,
    ModelUsageRecord,
    group_usage,
    summarize_usage,
)


class UsageProvider(ModelProvider):
    def __init__(self, name: str, response: str, usage: dict[str, int]) -> None:
        self.name = name
        self.response = response
        self.usage = usage
        self.calls = 0

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        return ModelResponse(
            text=self.response,
            model=request.model or self.name,
            provider=self.name,
            usage=self.usage,
        )


class FailingProvider(ModelProvider):
    def __init__(self, name: str = "primary") -> None:
        self.name = name
        self.calls = 0

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        from core.models.providers import ModelProviderError

        raise ModelProviderError("provider unavailable", retryable=False)


def test_pricing_catalog_estimates_cost_from_token_usage():
    catalog = ModelPricingCatalog(
        [ModelPricing("provider", "model", input_per_1m_tokens=1.0, output_per_1m_tokens=2.0)]
    )
    assert catalog.estimate(
        provider="provider",
        model="model",
        prompt_tokens=500_000,
        completion_tokens=100_000,
    ) == 0.7
    assert catalog.estimate(
        provider="missing",
        model="model",
        prompt_tokens=10,
        completion_tokens=10,
    ) is None


def test_router_records_usage_latency_cost_and_fallback():
    primary = FailingProvider()
    backup = UsageProvider(
        "backup",
        "ok",
        {"prompt_tokens": 1_000, "completion_tokens": 500, "total_tokens": 1_500},
    )
    store = InMemoryModelUsageStore()
    clock_values = iter([10.0, 10.10, 10.20, 10.35])
    catalog = ModelPricingCatalog(
        [ModelPricing("backup", "backup-model", input_per_1m_tokens=1.0, output_per_1m_tokens=2.0)]
    )
    router = ModelRouter(
        {"primary": primary, "backup": backup},
        (
            ModelRoute(ModelTask.CHAT, "primary", "primary-model", 100),
            ModelRoute(ModelTask.CHAT, "backup", "backup-model", 50),
        ),
        retry_policy=RetryPolicy(max_attempts=1),
        usage_store=store,
        pricing_catalog=catalog,
        clock=lambda: next(clock_values),
    )

    response = router.generate(ModelRequest(ModelTask.CHAT, input_text="hello"))

    assert response.provider == "backup"
    records = store.records()
    assert len(records) == 2
    assert records[0].success is False
    assert records[1].success is True
    assert records[1].fallback_used is True
    assert records[1].latency_ms == 150.0
    assert records[1].estimated_cost_usd == 0.002
    summary = router.usage_summary()
    assert summary.requests == 1
    assert summary.successful_requests == 1
    assert summary.fallback_requests == 1
    assert summary.total_tokens == 1_500
    assert summary.estimated_cost_usd == 0.002
    assert router.usage_summary_by_provider()["backup"].successful_requests == 1


def test_summary_distinguishes_failed_requests_from_recovered_fallbacks():
    request_id = UUID("00000000-0000-0000-0000-000000000001")
    failed_id = UUID("00000000-0000-0000-0000-000000000002")
    records = [
        ModelUsageRecord(request_id=request_id, provider="primary", model="p", task=ModelTask.CHAT),
        ModelUsageRecord(
            request_id=request_id,
            provider="backup",
            model="b",
            task=ModelTask.CHAT,
            success=True,
            fallback_used=True,
        ),
        ModelUsageRecord(
            request_id=failed_id,
            provider="primary",
            model="p",
            task=ModelTask.CHAT,
            success=False,
        ),
    ]
    summary = summarize_usage(records)
    assert summary.requests == 2
    assert summary.successful_requests == 1
    assert summary.failed_requests == 1
    assert summary.fallback_requests == 1
    assert summary.error_rate == 0.5
    assert group_usage(records, dimension="provider")["backup"].requests == 1


def test_json_usage_store_persists_records():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "usage.json"
        record = ModelUsageRecord(
            provider="provider",
            model="model",
            task=ModelTask.REASONING,
            prompt_tokens=4,
            completion_tokens=2,
            total_tokens=6,
            tokens_available=True,
            latency_ms=12.5,
            estimated_cost_usd=0.00001,
            metadata={"source": "test"},
        )
        JsonFileModelUsageStore(path).record(record)
        loaded = JsonFileModelUsageStore(path).records()
        assert len(loaded) == 1
        assert loaded[0].provider == "provider"
        assert loaded[0].total_tokens == 6
        assert loaded[0].task == ModelTask.REASONING
