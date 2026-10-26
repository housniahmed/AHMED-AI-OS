#!/usr/bin/env python3
"""Run a deterministic-scored benchmark against each configured model route.

This runner evaluates providers/models individually instead of letting adaptive
routing choose a winner, so every benchmark case has paired candidate results.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from core.evaluation.models import EvaluationCase, EvaluationRun, MetricResult
from core.evaluation.serialization import save_evaluation_run
from core.evaluation.service import DeterministicEvaluator, EvaluationFramework, EvaluationMetric
from core.models.contracts import ModelRequest, ModelTask
from core.models.resilience import InMemoryProviderHealthStore
from core.models.router import ModelRoute, ModelRouter
from core.models.usage import InMemoryModelUsageStore
from integrations.model_providers.openai_compatible import build_model_router_from_env


class DeterministicBenchmarkMetric(EvaluationMetric):
    """Score a case against its declared, deterministic expectation."""

    name = "benchmark_score"

    def score(self, case: EvaluationCase, output: Any) -> MetricResult:
        expected = case.expected
        threshold = float(case.metadata.get("benchmark_threshold", 0.75))
        if not isinstance(expected, dict):
            score = 0.0
            details = {"kind": "invalid_expected_spec"}
        else:
            kind = expected.get("kind")
            text = output if isinstance(output, str) else ""
            if kind == "required_terms":
                terms = expected["terms"]
                normalized = _normalize(text)
                matched = [term for term in terms if _normalize(term) in normalized]
                score = len(matched) / len(terms)
                details = {
                    "kind": kind,
                    "matched_terms": matched,
                    "term_count": len(terms),
                }
            elif kind == "exact_answer":
                target = _normalize(expected["answer"])
                score = 1.0 if _normalize(text) == target else 0.0
                details = {"kind": kind, "exact_match": score == 1.0}
            elif kind == "json_fields":
                fields = expected["fields"]
                parsed = _parse_json_object(text)
                matched = [
                    key for key, value in fields.items()
                    if parsed is not None and key in parsed and parsed[key] == value
                ]
                score = len(matched) / len(fields)
                details = {
                    "kind": kind,
                    "matched_fields": matched,
                    "field_count": len(fields),
                    "valid_json": parsed is not None,
                }
            else:
                score = 0.0
                details = {"kind": "unsupported_expected_spec", "declared_kind": str(kind)}
        return MetricResult(
            name=self.name,
            score=max(0.0, min(1.0, float(score))),
            passed=score >= threshold,
            threshold=threshold,
            details=details,
        )


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _parse_json_object(value: str) -> dict[str, Any] | None:
    candidate = value.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            candidate = "\n".join(lines[1:-1]).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid benchmark dataset JSON in {path}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("benchmark dataset must be a JSON object with schema_version=1")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("benchmark dataset 'cases' must be a non-empty JSON array")

    seen_ids: set[str] = set()
    validated: list[dict[str, Any]] = []
    for index, raw in enumerate(cases):
        if not isinstance(raw, dict):
            raise ValueError(f"case {index} must be a JSON object")
        case_id = str(raw.get("id", "")).strip()
        name = str(raw.get("name", "")).strip()
        prompt = raw.get("input")
        try:
            task = ModelTask(str(raw.get("task", "")))
        except ValueError as exc:
            raise ValueError(f"case {index} has an unsupported task") from exc
        expected = raw.get("expected")
        threshold = raw.get("threshold", 0.75)
        if not case_id or not name or not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"case {index} requires non-empty id/name/input")
        if case_id in seen_ids:
            raise ValueError(f"duplicate benchmark case id: {case_id}")
        if not isinstance(expected, dict):
            raise ValueError(f"case {case_id}: expected must be a JSON object")
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            raise ValueError(f"case {case_id}: threshold must be numeric and between 0 and 1")
        _validate_expected(case_id, expected)
        seen_ids.add(case_id)
        validated.append({
            "id": case_id,
            "name": name,
            "input": prompt,
            "task": task,
            "expected": expected,
            "threshold": float(threshold),
        })
    return validated


def _validate_expected(case_id: str, expected: dict[str, Any]) -> None:
    kind = expected.get("kind")
    if kind == "required_terms":
        terms = expected.get("terms")
        if not isinstance(terms, list) or not terms or any(not isinstance(item, str) or not item.strip() for item in terms):
            raise ValueError(f"case {case_id}: required_terms needs a non-empty list of terms")
    elif kind == "exact_answer":
        if not isinstance(expected.get("answer"), str) or not expected["answer"].strip():
            raise ValueError(f"case {case_id}: exact_answer needs a non-empty answer string")
    elif kind == "json_fields":
        fields = expected.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise ValueError(f"case {case_id}: json_fields needs a non-empty fields object")
    else:
        raise ValueError(f"case {case_id}: unsupported expected kind {kind!r}")


def _route_candidates(router: ModelRouter, tasks: set[ModelTask]) -> dict[ModelTask, tuple[ModelRoute, ...]]:
    by_task: dict[ModelTask, dict[tuple[str, str], ModelRoute]] = {task: {} for task in tasks}
    health = router.provider_status()
    now = router.clock()
    for route in router.routes:
        if route.task not in tasks or route.provider not in router.providers:
            continue
        state = health.get(route.provider)
        if state is not None:
            if not state.enabled:
                continue
            if state.circuit_open and (
                state.cooldown_until is None or now < state.cooldown_until
            ):
                continue
        by_task[route.task][(route.provider, route.model)] = route
    return {
        task: tuple(sorted(routes.values(), key=lambda item: (item.priority * -1, item.provider, item.model)))
        for task, routes in by_task.items()
    }


def _isolated_router(base: ModelRouter, route: ModelRoute) -> ModelRouter:
    """Build an independent one-route router without writing production telemetry."""
    health_store = InMemoryProviderHealthStore()
    initial_state = base.provider_status().get(route.provider)
    if initial_state is not None:
        health_store.save(route.provider, initial_state)
    return ModelRouter(
        providers={route.provider: base.providers[route.provider]},
        routes=(route,),
        retry_policy=base.retry_policy,
        circuit_policy=base.circuit_policy,
        health_store=health_store,
        usage_store=InMemoryModelUsageStore(),
        pricing_catalog=base.pricing_catalog,
        adaptive_engine=None,
        clock=base.clock,
        sleeper=base.sleeper,
    )


def _build_evaluation_run(
    base_router: ModelRouter,
    dataset: list[dict[str, Any]],
    *,
    limit_per_task: int,
    max_tokens: int,
    temperature: float,
) -> tuple[EvaluationRun, dict[str, Any]]:
    tasks = {item["task"] for item in dataset}
    candidates = _route_candidates(base_router, tasks)
    for task in sorted(tasks, key=lambda item: item.value):
        if len(candidates.get(task, ())) < 2:
            raise ValueError(
                f"task={task.value} needs at least two configured provider/model routes; "
                f"found {len(candidates.get(task, ())) }"
            )

    selected_cases = {
        task: [item for item in dataset if item["task"] == task][:limit_per_task]
        for task in tasks
    }
    route_lookup = {
        (route.task, route.provider, route.model): route
        for task_routes in candidates.values()
        for route in task_routes
    }
    evaluation_cases: list[EvaluationCase] = []
    for task in sorted(tasks, key=lambda item: item.value):
        for case in selected_cases[task]:
            for route in candidates[task]:
                evaluation_cases.append(
                    EvaluationCase(
                        name=case["name"],
                        input=case["input"],
                        expected=case["expected"],
                        metadata={
                            "provider": route.provider,
                            "model": route.model,
                            "task": task.value,
                            "benchmark_case_id": case["id"],
                            "benchmark_threshold": case["threshold"],
                        },
                    )
                )

    def runner(case: EvaluationCase) -> str:
        metadata = case.metadata
        task = ModelTask(str(metadata["task"]))
        key = (task, str(metadata["provider"]), str(metadata["model"]))
        # Each candidate/case receives fresh local health and usage stores so
        # benchmark failures cannot open the production circuit or pollute B40.
        response = _isolated_router(base_router, route_lookup[key]).generate(
            ModelRequest(
                task=task,
                input_text=str(case.input),
                model=str(metadata["model"]),
                max_tokens=max_tokens,
                temperature=temperature,
                metadata={"benchmark_case_id": metadata["benchmark_case_id"]},
            )
        )
        return response.text

    framework = EvaluationFramework(DeterministicEvaluator([DeterministicBenchmarkMetric()]))
    run = framework.run(evaluation_cases, runner)
    summary = EvaluationFramework.summary(run)
    by_task = {}
    for task in sorted(tasks, key=lambda item: item.value):
        task_results = [result for result in run.results if result.metadata.get("task") == task.value]
        by_task[task.value] = {
            "benchmark_cases": len(selected_cases[task]),
            "candidate_routes": [
                {"provider": route.provider, "model": route.model}
                for route in candidates[task]
            ],
            "result_count": len(task_results),
            "passed": sum(result.status.value == "passed" for result in task_results),
            "failed": sum(result.status.value == "failed" for result in task_results),
            "errors": sum(result.status.value == "error" for result in task_results),
        }
    return run, {"summary": summary, "by_task": by_task, "logical_evaluation_calls": len(evaluation_cases)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute a B32 benchmark against each configured route and save paired results."
    )
    parser.add_argument("--dataset", required=True, type=Path, help="Version 1 JSON benchmark case set")
    parser.add_argument("--output", required=True, type=Path, help="Output path for the versioned B32 evaluation run JSON")
    parser.add_argument("--limit-per-task", type=int, default=10, help="Maximum paired benchmark cases per task (default: 10)")
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if not args.dataset.is_file():
            raise ValueError(f"benchmark dataset does not exist: {args.dataset}")
        if args.output.resolve() == args.dataset.resolve():
            raise ValueError("output path must not overwrite the benchmark dataset")
        if args.limit_per_task < 1 or args.max_tokens < 1:
            raise ValueError("limit-per-task and max-tokens must be >= 1")
        if not 0 <= args.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")

        dataset = _load_dataset(args.dataset)
        router = build_model_router_from_env()
        if router is None:
            raise ValueError(
                "no model providers configured; set MODEL_PROVIDER_* or MODEL_PROVIDER_IDS environment variables"
            )
        run, report = _build_evaluation_run(
            router,
            dataset,
            limit_per_task=args.limit_per_task,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        save_evaluation_run(run, args.output)
        output = {
            "evaluation_run_id": str(run.id),
            "output_path": str(args.output),
            "dataset_case_count": len(dataset),
            **report,
            "result_file_written": True,
            "logical_model_requests_submitted": report["logical_evaluation_calls"],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
        return 1 if report["summary"]["errors"] else 0
    except (OSError, ValueError, TypeError, KeyError, LookupError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
