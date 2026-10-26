import tempfile
from pathlib import Path

import pytest

from core.evaluation.models import EvaluationResult, EvaluationRun, EvaluationStatus, MetricResult
from core.models.adaptive import AdaptiveRoutingEngine, AdaptiveRoutingPolicy
from core.models.contracts import ModelTask
from core.models.policy_learning import (
    InMemoryPolicyLifecycleStore,
    JsonFilePolicyLifecycleStore,
    PolicyCandidateOutcome,
    PolicyDatasetBuilder,
    PolicyFeatureVector,
    PolicyOptimizationConfig,
    PolicyProposalStatus,
    PolicyTrainingSample,
    RoutingPolicyOptimizer,
)


def _sample(index: int, *, winning_model: str = "quality-model") -> PolicyTrainingSample:
    return PolicyTrainingSample(
        sample_id=f"benchmark-{index}",
        task=ModelTask.REASONING,
        candidates=(
            PolicyCandidateOutcome(
                "provider", "cheap-model",
                PolicyFeatureVector(reliability=0.95, latency=0.7, quality=0.60, cost=1.0),
                observed_quality=0.62,
            ),
            PolicyCandidateOutcome(
                "provider", "quality-model",
                PolicyFeatureVector(reliability=0.90, latency=0.55, quality=0.95, cost=0.25),
                observed_quality=0.96 if winning_model == "quality-model" else 0.50,
            ),
        ),
    )


def _service(store=None, **config):
    return RoutingPolicyOptimizer(
        store=store or InMemoryPolicyLifecycleStore(),
        config=PolicyOptimizationConfig(
            min_training_samples=2,
            min_validation_samples=2,
            min_mean_uplift=0.01,
            exploration_rate=1.0,
            **config,
        ),
        default_policy=AdaptiveRoutingPolicy(
            reliability_weight=0.60,
            latency_weight=0.15,
            quality_weight=0.10,
            cost_weight=0.15,
        ),
    )


def test_dataset_builder_requires_paired_evaluation_groups_and_features():
    run = EvaluationRun(results=(
        EvaluationResult(
            case_id=__import__("uuid").uuid4(),
            status=EvaluationStatus.PASSED,
            metrics=(MetricResult("quality", 0.9, True),),
            metadata={
                "provider": "p", "model": "a", "task": "reasoning",
                "benchmark_case_id": "case-1",
            },
        ),
        EvaluationResult(
            case_id=__import__("uuid").uuid4(),
            status=EvaluationStatus.FAILED,
            metrics=(MetricResult("quality", 0.4, False),),
            metadata={
                "provider": "p", "model": "b", "task": "reasoning",
                "benchmark_case_id": "case-1",
            },
        ),
        EvaluationResult(
            case_id=__import__("uuid").uuid4(),
            status=EvaluationStatus.PASSED,
            metrics=(MetricResult("quality", 1.0, True),),
            metadata={"provider": "p", "model": "solo", "task": "reasoning"},
        ),
    ))
    report = PolicyDatasetBuilder.from_evaluation_run(
        run,
        feature_resolver=lambda provider, model, task: PolicyFeatureVector(0.9, 0.8, 0.7, 0.6),
    )
    assert len(report.samples) == 1
    assert len(report.samples[0].candidates) == 2
    assert report.skipped_groups == 1
    assert report.skipped_results == 1


def test_policy_optimizer_proposes_but_does_not_auto_activate():
    service = _service()
    samples = tuple(_sample(i) for i in range(60))
    proposal = service.propose(ModelTask.REASONING, samples, dataset_id="offline-benchmark-v1")
    assert proposal.status in {
        PolicyProposalStatus.PENDING_APPROVAL,
        PolicyProposalStatus.INSUFFICIENT_EVIDENCE,
    }
    assert service.get_active_policy(ModelTask.REASONING) == proposal.baseline_policy
    if proposal.status is PolicyProposalStatus.PENDING_APPROVAL:
        assert proposal.stats.gate_eligible
        assert proposal.stats.validation_samples >= 2


def test_approval_requires_explicit_actor_and_current_revision():
    service = _service()
    # Ensure an active baseline before creating a proposal.
    baseline = service.ensure_baseline(ModelTask.REASONING)
    proposal = service.propose(ModelTask.REASONING, tuple(_sample(i) for i in range(100)))
    assert proposal.status is PolicyProposalStatus.PENDING_APPROVAL
    with pytest.raises(ValueError):
        service.approve(
            proposal.id, approver="", expected_revision=baseline.revision, reason="test"
        )
    revision = service.approve(
        proposal.id, approver="human-reviewer",
        expected_revision=baseline.revision, reason="benchmark uplift validated",
    )
    assert revision.revision == baseline.revision + 1
    assert service.get_active_policy(ModelTask.REASONING) == proposal.candidate_policy
    assert service.store.get_proposal(proposal.id).status is PolicyProposalStatus.ACTIVE


def test_stale_proposal_cannot_be_promoted():
    service = _service()
    baseline = service.ensure_baseline(ModelTask.REASONING)
    proposal = service.propose(ModelTask.REASONING, tuple(_sample(i) for i in range(100)))
    if proposal.status is not PolicyProposalStatus.PENDING_APPROVAL:
        pytest.skip("sample split or evidence did not pass gates for this deterministic candidate set")
    with pytest.raises(RuntimeError, match="stale"):
        service.approve(
            proposal.id, approver="human",
            expected_revision=baseline.revision + 1, reason="stale check",
        )
    assert service.store.get_proposal(proposal.id).status is PolicyProposalStatus.STALE


def test_rollback_restores_previous_active_policy():
    service = _service()
    baseline = service.ensure_baseline(ModelTask.REASONING)
    proposal = service.propose(ModelTask.REASONING, tuple(_sample(i) for i in range(100)))
    if proposal.status is not PolicyProposalStatus.PENDING_APPROVAL:
        pytest.skip("sample split or evidence did not pass gates for this deterministic candidate set")
    active = service.approve(
        proposal.id, approver="human",
        expected_revision=baseline.revision, reason="promote test policy",
    )
    rollback = service.rollback(
        ModelTask.REASONING, actor="human",
        expected_revision=active.revision, reason="regression observed",
    )
    assert rollback.policy == baseline.policy
    assert rollback.revision == active.revision + 1
    assert service.store.get_proposal(proposal.id).status is PolicyProposalStatus.ROLLED_BACK


def test_json_store_persists_revisions_proposals_and_audit():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "routing-policies.json"
        service = _service(JsonFilePolicyLifecycleStore(path))
        baseline = service.ensure_baseline(ModelTask.REASONING)
        proposal = service.propose(ModelTask.REASONING, tuple(_sample(i) for i in range(100)))
        loaded = JsonFilePolicyLifecycleStore(path)
        assert loaded.active_revision(ModelTask.REASONING).revision == baseline.revision
        assert loaded.get_proposal(proposal.id) is not None
        assert loaded.audit_events()


def test_adaptive_engine_reads_approved_task_specific_policy():
    service = _service()
    baseline = service.ensure_baseline(ModelTask.REASONING)
    engine = AdaptiveRoutingEngine(policy=baseline.policy, policy_source=service)
    assert engine._policy_for(ModelTask.REASONING) == baseline.policy
