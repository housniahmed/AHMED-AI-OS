"""B43 offline routing-policy optimization with statistical gates and human approval.

B43 learns policy weights from paired benchmark outcomes. It proposes changes;
it never activates a policy until an explicit approval call is made.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, fields, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Callable, Protocol
from uuid import UUID, uuid4

from core.evaluation.models import EvaluationRun, EvaluationStatus
from core.models.adaptive import AdaptiveRoutingPolicy
from core.models.contracts import ModelTask


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class PolicyFeatureVector:
    """Normalized B39/B40/B42 features for one candidate (each value in [0, 1])."""

    reliability: float
    latency: float
    quality: float
    cost: float
    priority: int = 0

    def __post_init__(self) -> None:
        for name in ("reliability", "latency", "quality", "cost"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} feature must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class PolicyCandidateOutcome:
    provider: str
    model: str
    features: PolicyFeatureVector
    observed_quality: float

    def __post_init__(self) -> None:
        if not self.provider or not self.model:
            raise ValueError("candidate provider and model are required")
        if not 0 <= self.observed_quality <= 1:
            raise ValueError("observed_quality must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class PolicyTrainingSample:
    sample_id: str
    task: ModelTask
    candidates: tuple[PolicyCandidateOutcome, ...]

    def __post_init__(self) -> None:
        if not self.sample_id.strip():
            raise ValueError("sample_id is required")
        if len(self.candidates) < 2:
            raise ValueError("a policy training sample needs at least two evaluated candidates")
        keys = [(item.provider, item.model) for item in self.candidates]
        if len(set(keys)) != len(keys):
            raise ValueError("sample candidate provider/model pairs must be unique")


@dataclass(frozen=True, slots=True)
class DatasetBuildReport:
    samples: tuple[PolicyTrainingSample, ...]
    skipped_results: int
    skipped_groups: int
    reasons: tuple[str, ...] = ()


FeatureResolver = Callable[[str, str, ModelTask], PolicyFeatureVector | None]


class PolicyDatasetBuilder:
    """Build paired counterfactual samples from B32 evaluations plus B39/B40/B42 features."""

    GROUP_KEYS = ("benchmark_case_id", "dataset_case_id", "evaluation_group_id")

    @classmethod
    def from_evaluation_run(
        cls,
        run: EvaluationRun,
        *,
        feature_resolver: FeatureResolver,
        metric_weights: dict[str, float] | None = None,
    ) -> DatasetBuildReport:
        weights = metric_weights or {}
        grouped: dict[tuple[ModelTask, str], dict[tuple[str, str], list[Any]]] = {}
        skipped = 0
        reasons: list[str] = []

        for result in run.results:
            metadata = result.metadata
            provider = str(metadata.get("provider", "")).strip()
            model = str(metadata.get("model", "")).strip()
            task_raw = str(metadata.get("task", "")).strip()
            group_id = next(
                (
                    str(metadata.get(key)).strip()
                    for key in cls.GROUP_KEYS
                    if metadata.get(key) is not None and str(metadata.get(key)).strip()
                ),
                "",
            )
            if not provider or not model or not task_raw or not group_id:
                skipped += 1
                reasons.append(f"result {result.case_id}: missing provider/model/task/benchmark group")
                continue
            if result.status is EvaluationStatus.ERROR or not result.metrics:
                skipped += 1
                reasons.append(f"result {result.case_id}: no usable metric outcome")
                continue
            try:
                task = ModelTask(task_raw)
            except ValueError:
                skipped += 1
                reasons.append(f"result {result.case_id}: unsupported task {task_raw}")
                continue

            scores = {metric.name: metric.score for metric in result.metrics if metric.name}
            if not scores:
                skipped += 1
                reasons.append(f"result {result.case_id}: no named metric scores")
                continue
            selected = [
                (scores[name], weight)
                for name, weight in weights.items()
                if name in scores and weight > 0
            ]
            if selected:
                denominator = sum(weight for _, weight in selected)
                outcome = sum(score * weight for score, weight in selected) / denominator
            else:
                outcome = mean(scores.values())

            try:
                features = feature_resolver(provider, model, task)
            except Exception as exc:
                skipped += 1
                reasons.append(f"result {result.case_id}: feature resolution failed: {type(exc).__name__}")
                continue
            if features is None:
                skipped += 1
                reasons.append(f"result {result.case_id}: no routing feature snapshot")
                continue

            key = (task, group_id)
            candidate_key = (provider, model)
            grouped.setdefault(key, {}).setdefault(candidate_key, []).append((features, outcome))

        samples: list[PolicyTrainingSample] = []
        skipped_groups = 0
        for (task, group_id), candidates in sorted(
            grouped.items(),
            key=lambda item: (item[0][0].value, item[0][1]),
        ):
            if len(candidates) < 2:
                skipped_groups += 1
                continue
            outcomes: list[PolicyCandidateOutcome] = []
            for (provider, model), values in sorted(candidates.items()):
                feature = values[-1][0]
                # Multiple results for the same model in the same benchmark group
                # are aggregated so one model cannot gain weight from duplicate records.
                outcome = mean(value for _, value in values)
                outcomes.append(
                    PolicyCandidateOutcome(
                        provider=provider,
                        model=model,
                        features=feature,
                        observed_quality=outcome,
                    )
                )
            samples.append(
                PolicyTrainingSample(
                    sample_id=f"{task.value}:{group_id}",
                    task=task,
                    candidates=tuple(outcomes),
                )
            )

        return DatasetBuildReport(
            samples=tuple(samples),
            skipped_results=skipped,
            skipped_groups=skipped_groups,
            reasons=tuple(reasons),
        )


@dataclass(frozen=True, slots=True)
class PolicyOptimizationConfig:
    min_training_samples: int = 20
    min_validation_samples: int = 20
    min_mean_uplift: float = 0.02
    confidence_z: float = 1.96
    exploration_rate: float = 0.35

    def __post_init__(self) -> None:
        if self.min_training_samples < 1 or self.min_validation_samples < 2:
            raise ValueError("training samples must be >= 1 and validation samples >= 2")
        if not -1 <= self.min_mean_uplift <= 1:
            raise ValueError("min_mean_uplift must be between -1 and 1")
        if self.confidence_z <= 0:
            raise ValueError("confidence_z must be > 0")
        if not 0 < self.exploration_rate <= 1:
            raise ValueError("exploration_rate must be in (0, 1]")


@dataclass(frozen=True, slots=True)
class PolicyComparisonStats:
    training_samples: int
    validation_samples: int
    baseline_validation_score: float
    candidate_validation_score: float
    mean_uplift: float
    standard_error: float
    confidence_lower_bound: float
    gate_eligible: bool


class PolicyProposalStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ACTIVE = "active"
    REJECTED = "rejected"
    STALE = "stale"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True, slots=True)
class PolicyOptimizationProposal:
    id: UUID
    task: ModelTask
    baseline_revision: int
    baseline_policy: AdaptiveRoutingPolicy
    candidate_policy: AdaptiveRoutingPolicy
    stats: PolicyComparisonStats
    status: PolicyProposalStatus
    created_at: datetime = field(default_factory=utc_now)
    dataset_id: str | None = None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class PolicyRevision:
    task: ModelTask
    revision: int
    policy: AdaptiveRoutingPolicy
    changed_by: str
    reason: str
    created_at: datetime = field(default_factory=utc_now)
    proposal_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("policy revision must be >= 1")
        if not self.changed_by.strip():
            raise ValueError("changed_by is required")
        if not self.reason.strip():
            raise ValueError("revision reason is required")


@dataclass(frozen=True, slots=True)
class PolicyAuditEvent:
    action: str
    actor: str
    task: ModelTask
    reason: str
    revision: int | None = None
    proposal_id: UUID | None = None
    details: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=utc_now)
    id: UUID = field(default_factory=uuid4)


class PolicyLifecycleStore(Protocol):
    def active_revision(self, task: ModelTask) -> PolicyRevision | None: ...
    def revision_history(self, task: ModelTask) -> tuple[PolicyRevision, ...]: ...
    def save_revision(self, revision: PolicyRevision, *, activate: bool = True) -> None: ...
    def save_proposal(self, proposal: PolicyOptimizationProposal) -> None: ...
    def get_proposal(self, proposal_id: UUID) -> PolicyOptimizationProposal | None: ...
    def append_audit(self, event: PolicyAuditEvent) -> None: ...
    def audit_events(self) -> tuple[PolicyAuditEvent, ...]: ...


class InMemoryPolicyLifecycleStore:
    def __init__(self) -> None:
        self._revisions: dict[tuple[ModelTask, int], PolicyRevision] = {}
        self._active: dict[ModelTask, int] = {}
        self._proposals: dict[UUID, PolicyOptimizationProposal] = {}
        self._audit: list[PolicyAuditEvent] = []

    def active_revision(self, task: ModelTask) -> PolicyRevision | None:
        revision = self._active.get(task)
        return self._revisions.get((task, revision)) if revision is not None else None

    def revision_history(self, task: ModelTask) -> tuple[PolicyRevision, ...]:
        return tuple(
            sorted(
                (item for (item_task, _), item in self._revisions.items() if item_task == task),
                key=lambda item: item.revision,
            )
        )

    def save_revision(self, revision: PolicyRevision, *, activate: bool = True) -> None:
        self._revisions[(revision.task, revision.revision)] = revision
        if activate:
            self._active[revision.task] = revision.revision
        self._changed()

    def save_proposal(self, proposal: PolicyOptimizationProposal) -> None:
        self._proposals[proposal.id] = proposal
        self._changed()

    def get_proposal(self, proposal_id: UUID) -> PolicyOptimizationProposal | None:
        return self._proposals.get(proposal_id)

    def append_audit(self, event: PolicyAuditEvent) -> None:
        self._audit.append(event)
        self._changed()

    def audit_events(self) -> tuple[PolicyAuditEvent, ...]:
        return tuple(self._audit)

    def proposals(self) -> tuple[PolicyOptimizationProposal, ...]:
        return tuple(self._proposals.values())

    def _changed(self) -> None:
        """Persistence hook for durable stores."""


class JsonFilePolicyLifecycleStore(InMemoryPolicyLifecycleStore):
    """Durable JSON store for revisions, proposals, active pointers, and audit events.

    This implementation is single-process. Use a transactional database store for
    multi-worker deployment and concurrent approval workflows.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        super().__init__()
        self._load()
        
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid routing policy store: {self.path}") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("unsupported routing policy store schema")
        for raw in payload.get("revisions", []):
            revision = self._revision_from_dict(raw)
            self._revisions[(revision.task, revision.revision)] = revision
        self._active = {
            ModelTask(task): int(revision)
            for task, revision in payload.get("active", {}).items()
        }
        for raw in payload.get("proposals", []):
            proposal = self._proposal_from_dict(raw)
            self._proposals[proposal.id] = proposal
        self._audit = [self._audit_from_dict(raw) for raw in payload.get("audit", [])]

    def _changed(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "active": {task.value: revision for task, revision in self._active.items()},
            "revisions": [self._revision_to_dict(item) for item in self._revisions.values()],
            "proposals": [self._proposal_to_dict(item) for item in self._proposals.values()],
            "audit": [self._audit_to_dict(item) for item in self._audit],
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _policy_to_dict(policy: AdaptiveRoutingPolicy) -> dict[str, Any]:
        return asdict(policy)

    @staticmethod
    def _policy_from_dict(payload: dict[str, Any]) -> AdaptiveRoutingPolicy:
        allowed = {item.name for item in fields(AdaptiveRoutingPolicy)}
        return AdaptiveRoutingPolicy(**{key: value for key, value in payload.items() if key in allowed})

    @classmethod
    def _revision_to_dict(cls, item: PolicyRevision) -> dict[str, Any]:
        return {
            "task": item.task.value,
            "revision": item.revision,
            "policy": cls._policy_to_dict(item.policy),
            "changed_by": item.changed_by,
            "reason": item.reason,
            "created_at": item.created_at.isoformat(),
            "proposal_id": str(item.proposal_id) if item.proposal_id else None,
        }

    @classmethod
    def _revision_from_dict(cls, raw: object) -> PolicyRevision:
        if not isinstance(raw, dict):
            raise ValueError("policy revision must be an object")
        try:
            return PolicyRevision(
                task=ModelTask(str(raw["task"])),
                revision=int(raw["revision"]),
                policy=cls._policy_from_dict(dict(raw["policy"])),
                changed_by=str(raw["changed_by"]),
                reason=str(raw["reason"]),
                created_at=datetime.fromisoformat(str(raw["created_at"])),
                proposal_id=UUID(str(raw["proposal_id"])) if raw.get("proposal_id") else None,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid policy revision") from exc

    @classmethod
    def _proposal_to_dict(cls, item: PolicyOptimizationProposal) -> dict[str, Any]:
        return {
            "id": str(item.id),
            "task": item.task.value,
            "baseline_revision": item.baseline_revision,
            "baseline_policy": cls._policy_to_dict(item.baseline_policy),
            "candidate_policy": cls._policy_to_dict(item.candidate_policy),
            "stats": asdict(item.stats),
            "status": item.status.value,
            "created_at": item.created_at.isoformat(),
            "dataset_id": item.dataset_id,
            "reason": item.reason,
        }

    @classmethod
    def _proposal_from_dict(cls, raw: object) -> PolicyOptimizationProposal:
        if not isinstance(raw, dict):
            raise ValueError("policy proposal must be an object")
        try:
            stats = dict(raw["stats"])
            return PolicyOptimizationProposal(
                id=UUID(str(raw["id"])),
                task=ModelTask(str(raw["task"])),
                baseline_revision=int(raw["baseline_revision"]),
                baseline_policy=cls._policy_from_dict(dict(raw["baseline_policy"])),
                candidate_policy=cls._policy_from_dict(dict(raw["candidate_policy"])),
                stats=PolicyComparisonStats(
                    training_samples=int(stats["training_samples"]),
                    validation_samples=int(stats["validation_samples"]),
                    baseline_validation_score=float(stats["baseline_validation_score"]),
                    candidate_validation_score=float(stats["candidate_validation_score"]),
                    mean_uplift=float(stats["mean_uplift"]),
                    standard_error=float(stats["standard_error"]),
                    confidence_lower_bound=float(stats["confidence_lower_bound"]),
                    gate_eligible=bool(stats["gate_eligible"]),
                ),
                status=PolicyProposalStatus(str(raw["status"])),
                created_at=datetime.fromisoformat(str(raw["created_at"])),
                dataset_id=raw.get("dataset_id"),
                reason=str(raw.get("reason", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid policy proposal") from exc

    @staticmethod
    def _audit_to_dict(item: PolicyAuditEvent) -> dict[str, Any]:
        return {
            "id": str(item.id),
            "action": item.action,
            "actor": item.actor,
            "task": item.task.value,
            "reason": item.reason,
            "revision": item.revision,
            "proposal_id": str(item.proposal_id) if item.proposal_id else None,
            "details": item.details,
            "occurred_at": item.occurred_at.isoformat(),
        }

    @staticmethod
    def _audit_from_dict(raw: object) -> PolicyAuditEvent:
        if not isinstance(raw, dict):
            raise ValueError("policy audit event must be an object")
        try:
            return PolicyAuditEvent(
                id=UUID(str(raw["id"])),
                action=str(raw["action"]),
                actor=str(raw["actor"]),
                task=ModelTask(str(raw["task"])),
                reason=str(raw["reason"]),
                revision=int(raw["revision"]) if raw.get("revision") is not None else None,
                proposal_id=UUID(str(raw["proposal_id"])) if raw.get("proposal_id") else None,
                details=dict(raw.get("details", {})),
                occurred_at=datetime.fromisoformat(str(raw["occurred_at"])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid policy audit event") from exc


class RoutingPolicyOptimizer:
    """Optimize weights offline; approval and activation are separate explicit operations."""

    RECIPES = {
        "reliability": (0.60, 0.15, 0.15, 0.10),
        "latency": (0.20, 0.50, 0.15, 0.15),
        "quality": (0.15, 0.10, 0.60, 0.15),
        "cost": (0.20, 0.15, 0.15, 0.50),
        "balanced": (0.25, 0.25, 0.25, 0.25),
    }

    def __init__(
        self,
        *,
        store: PolicyLifecycleStore | None = None,
        config: PolicyOptimizationConfig | None = None,
        default_policy: AdaptiveRoutingPolicy | None = None,
    ) -> None:
        self.store = store or InMemoryPolicyLifecycleStore()
        self.config = config or PolicyOptimizationConfig()
        self.default_policy = default_policy or AdaptiveRoutingPolicy()

    def get_active_policy(self, task: ModelTask) -> AdaptiveRoutingPolicy | None:
        revision = self.store.active_revision(task)
        return revision.policy if revision else None

    def ensure_baseline(
        self,
        task: ModelTask,
        *,
        policy: AdaptiveRoutingPolicy | None = None,
        actor: str = "system",
    ) -> PolicyRevision:
        active = self.store.active_revision(task)
        if active is not None:
            return active
        baseline = policy or self.default_policy
        revision = PolicyRevision(
            task=task,
            revision=1,
            policy=baseline,
            changed_by=actor,
            reason="initial baseline policy",
        )
        self.store.save_revision(revision)
        self.store.append_audit(
            PolicyAuditEvent(
                action="baseline_initialized",
                actor=actor,
                task=task,
                revision=revision.revision,
                reason=revision.reason,
            )
        )
        return revision

    def propose(
        self,
        task: ModelTask,
        samples: tuple[PolicyTrainingSample, ...] | list[PolicyTrainingSample],
        *,
        baseline_policy: AdaptiveRoutingPolicy | None = None,
        dataset_id: str | None = None,
    ) -> PolicyOptimizationProposal:
        baseline_revision = self.ensure_baseline(task, policy=baseline_policy)
        baseline = baseline_revision.policy
        usable = tuple(sample for sample in samples if sample.task == task and len(sample.candidates) >= 2)
        training, validation = self._split(usable)

        candidates = self.candidate_policies(baseline)
        training_n = len(training)
        validation_n = len(validation)
        baseline_validation_scores = self._policy_outcomes(baseline, validation)
        baseline_score = mean(baseline_validation_scores) if baseline_validation_scores else 0.0

        chosen = baseline
        chosen_training_score = (
            mean(self._policy_outcomes(baseline, training)) if training else 0.0
        )
        for candidate in candidates:
            candidate_score = (
                mean(self._policy_outcomes(candidate, training)) if training else 0.0
            )
            if candidate_score > chosen_training_score + 1e-12:
                chosen = candidate
                chosen_training_score = candidate_score

        candidate_validation_scores = self._policy_outcomes(chosen, validation)
        candidate_score = mean(candidate_validation_scores) if candidate_validation_scores else 0.0
        deltas = [
            candidate_outcome - baseline_outcome
            for candidate_outcome, baseline_outcome in zip(
                candidate_validation_scores,
                baseline_validation_scores,
            )
        ]
        mean_uplift = mean(deltas) if deltas else 0.0
        standard_error = (
            stdev(deltas) / math.sqrt(len(deltas))
            if len(deltas) >= 2
            else 1.0
        )
        # With fewer than two paired validation observations, use the worst-case
        # uncertainty bound so a policy can never pass statistical gates.
        lower_bound = (
            mean_uplift - self.config.confidence_z * standard_error
            if len(deltas) >= 2
            else -1.0
        )
        enough_data = (
            training_n >= self.config.min_training_samples
            and validation_n >= self.config.min_validation_samples
        )
        eligible = (
            enough_data
            and chosen != baseline
            and mean_uplift >= self.config.min_mean_uplift
            and lower_bound > 0
        )
        stats = PolicyComparisonStats(
            training_samples=training_n,
            validation_samples=validation_n,
            baseline_validation_score=baseline_score,
            candidate_validation_score=candidate_score,
            mean_uplift=mean_uplift,
            standard_error=standard_error,
            confidence_lower_bound=lower_bound,
            gate_eligible=eligible,
        )
        status = (
            PolicyProposalStatus.PENDING_APPROVAL
            if eligible
            else PolicyProposalStatus.INSUFFICIENT_EVIDENCE
        )
        reason = (
            "candidate passed sample, uplift, and confidence gates; explicit approval required"
            if eligible
            else self._gate_reason(stats, chosen == baseline)
        )
        proposal = PolicyOptimizationProposal(
            id=uuid4(),
            task=task,
            baseline_revision=baseline_revision.revision,
            baseline_policy=baseline,
            candidate_policy=chosen,
            stats=stats,
            status=status,
            dataset_id=dataset_id,
            reason=reason,
        )
        self.store.save_proposal(proposal)
        self.store.append_audit(
            PolicyAuditEvent(
                action="proposal_created",
                actor="optimizer",
                task=task,
                revision=baseline_revision.revision,
                proposal_id=proposal.id,
                reason=reason,
                details={
                    "training_samples": training_n,
                    "validation_samples": validation_n,
                    "uplift": mean_uplift,
                    "confidence_lower_bound": lower_bound if math.isfinite(lower_bound) else None,
                    "gate_eligible": eligible,
                },
            )
        )
        return proposal

    def approve(
        self,
        proposal_id: UUID,
        *,
        approver: str,
        expected_revision: int,
        reason: str,
    ) -> PolicyRevision:
        if not approver.strip() or not reason.strip():
            raise ValueError("approver and approval reason are required")
        proposal = self._required_proposal(proposal_id)
        if proposal.status is not PolicyProposalStatus.PENDING_APPROVAL or not proposal.stats.gate_eligible:
            raise ValueError("only proposals that pass all gates can be approved")
        active = self.store.active_revision(proposal.task)
        current_revision = active.revision if active else 0
        if current_revision != expected_revision or current_revision != proposal.baseline_revision:
            stale = replace(
                proposal,
                status=PolicyProposalStatus.STALE,
                reason="approval rejected: active policy revision changed",
            )
            self.store.save_proposal(stale)
            self.store.append_audit(
                PolicyAuditEvent(
                    action="proposal_stale",
                    actor=approver,
                    task=proposal.task,
                    revision=current_revision,
                    proposal_id=proposal.id,
                    reason=stale.reason,
                )
            )
            raise RuntimeError("stale routing policy proposal; regenerate against the active revision")

        revision = PolicyRevision(
            task=proposal.task,
            revision=current_revision + 1,
            policy=proposal.candidate_policy,
            changed_by=approver,
            reason=reason,
            proposal_id=proposal.id,
        )
        self.store.save_revision(revision, activate=True)
        self.store.save_proposal(
            replace(
                proposal,
                status=PolicyProposalStatus.ACTIVE,
                reason=f"approved by {approver}: {reason}",
            )
        )
        self.store.append_audit(
            PolicyAuditEvent(
                action="policy_activated",
                actor=approver,
                task=proposal.task,
                revision=revision.revision,
                proposal_id=proposal.id,
                reason=reason,
                details={"previous_revision": current_revision},
            )
        )
        return revision

    def reject(self, proposal_id: UUID, *, actor: str, reason: str) -> PolicyOptimizationProposal:
        if not actor.strip() or not reason.strip():
            raise ValueError("actor and rejection reason are required")
        proposal = self._required_proposal(proposal_id)
        if proposal.status is not PolicyProposalStatus.PENDING_APPROVAL:
            raise ValueError("only pending proposals can be rejected")
        rejected = replace(
            proposal,
            status=PolicyProposalStatus.REJECTED,
            reason=f"rejected by {actor}: {reason}",
        )
        self.store.save_proposal(rejected)
        self.store.append_audit(
            PolicyAuditEvent(
                action="proposal_rejected",
                actor=actor,
                task=proposal.task,
                revision=proposal.baseline_revision,
                proposal_id=proposal.id,
                reason=reason,
            )
        )
        return rejected

    def rollback(
        self,
        task: ModelTask,
        *,
        actor: str,
        expected_revision: int,
        reason: str,
    ) -> PolicyRevision:
        if not actor.strip() or not reason.strip():
            raise ValueError("actor and rollback reason are required")
        active = self.store.active_revision(task)
        if active is None:
            raise LookupError(f"no active policy exists for task={task.value}")
        if active.revision != expected_revision:
            raise RuntimeError("stale rollback request; active revision changed")
        previous = [
            item for item in self.store.revision_history(task)
            if item.revision < active.revision
        ]
        if not previous:
            raise LookupError("no previous policy revision exists for rollback")
        target = max(previous, key=lambda item: item.revision)
        rollback_revision = PolicyRevision(
            task=task,
            revision=active.revision + 1,
            policy=target.policy,
            changed_by=actor,
            reason=f"rollback to revision {target.revision}: {reason}",
        )
        self.store.save_revision(rollback_revision, activate=True)
        if active.proposal_id:
            proposal = self.store.get_proposal(active.proposal_id)
            if proposal is not None:
                self.store.save_proposal(
                    replace(
                        proposal,
                        status=PolicyProposalStatus.ROLLED_BACK,
                        reason=f"rolled back by {actor}: {reason}",
                    )
                )
        self.store.append_audit(
            PolicyAuditEvent(
                action="policy_rolled_back",
                actor=actor,
                task=task,
                revision=rollback_revision.revision,
                reason=reason,
                details={
                    "rolled_back_from_revision": active.revision,
                    "restored_policy_revision": target.revision,
                },
            )
        )
        return rollback_revision

    def candidate_policies(self, baseline: AdaptiveRoutingPolicy) -> tuple[AdaptiveRoutingPolicy, ...]:
        base_weights = baseline.normalized_weights
        generated: list[AdaptiveRoutingPolicy] = [baseline]
        for recipe in self.RECIPES.values():
            rate = self.config.exploration_rate
            weights = tuple(
                (1 - rate) * current + rate * target
                for current, target in zip(base_weights, recipe)
            )
            policy = replace(
                baseline,
                reliability_weight=weights[0],
                latency_weight=weights[1],
                quality_weight=weights[2],
                cost_weight=weights[3],
            )
            if not any(self._same_weights(policy, item) for item in generated):
                generated.append(policy)
        return tuple(generated)

    @staticmethod
    def _same_weights(left: AdaptiveRoutingPolicy, right: AdaptiveRoutingPolicy) -> bool:
        return all(
            math.isclose(a, b, abs_tol=1e-8)
            for a, b in zip(left.normalized_weights, right.normalized_weights)
        )

    @staticmethod
    def _score_candidate(policy: AdaptiveRoutingPolicy, candidate: PolicyCandidateOutcome) -> float:
        rw, lw, qw, cw = policy.normalized_weights
        features = candidate.features
        return (
            rw * features.reliability
            + lw * features.latency
            + qw * features.quality
            + cw * features.cost
        )

    @classmethod
    def _selected_outcome(cls, policy: AdaptiveRoutingPolicy, sample: PolicyTrainingSample) -> float:
        selected = max(
            sample.candidates,
            key=lambda candidate: (
                cls._score_candidate(policy, candidate),
                candidate.features.priority,
                candidate.provider,
                candidate.model,
            ),
        )
        return selected.observed_quality

    @classmethod
    def _policy_outcomes(
        cls,
        policy: AdaptiveRoutingPolicy,
        samples: tuple[PolicyTrainingSample, ...] | list[PolicyTrainingSample],
    ) -> list[float]:
        return [cls._selected_outcome(policy, sample) for sample in samples]

    @staticmethod
    def _split(
        samples: tuple[PolicyTrainingSample, ...],
    ) -> tuple[tuple[PolicyTrainingSample, ...], tuple[PolicyTrainingSample, ...]]:
        """Stable split by sample ID hash to avoid ordering-dependent train/validation leakage."""
        training: list[PolicyTrainingSample] = []
        validation: list[PolicyTrainingSample] = []
        for sample in samples:
            bucket = int(hashlib.sha256(sample.sample_id.encode("utf-8")).hexdigest()[:8], 16) % 5
            (validation if bucket == 0 else training).append(sample)
        return tuple(training), tuple(validation)

    def _required_proposal(self, proposal_id: UUID) -> PolicyOptimizationProposal:
        proposal = self.store.get_proposal(proposal_id)
        if proposal is None:
            raise KeyError(f"unknown policy proposal: {proposal_id}")
        return proposal

    def _gate_reason(self, stats: PolicyComparisonStats, candidate_is_baseline: bool) -> str:
        if candidate_is_baseline:
            return "no candidate outperformed the active policy on training data"
        if stats.training_samples == 0 or stats.validation_samples == 0:
            return "insufficient paired training/validation samples"
        if not stats.gate_eligible:
            return (
                f"promotion blocked: uplift={stats.mean_uplift:.4f}, "
                f"confidence_lower_bound={stats.confidence_lower_bound:.4f}, "
                f"training={stats.training_samples}/{self.config.min_training_samples}, "
                f"validation={stats.validation_samples}/{self.config.min_validation_samples}; "
                f"minimum uplift={self.config.min_mean_uplift:.4f}"
            )
        return "promotion blocked"


class PolicyRevisionConflict(RuntimeError):
    """Raised when a policy change is based on a stale revision."""
