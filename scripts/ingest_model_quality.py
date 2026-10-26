#!/usr/bin/env python3
"""Ingest an older B32 evaluation run into the durable B42 quality profile store.

Use this on historical evaluations before freezing features for a future
benchmark. Ingesting the target benchmark itself makes the profile too recent
to be used as a feature for that same run; B43 rejects that timestamp leakage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.evaluation.serialization import load_evaluation_run
from core.models.quality import (
    JsonFileQualityProfileStore,
    ModelQualityIntelligence,
    QualityLearningPolicy,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Learn B42 exact-model/family quality profiles from an older B32 evaluation run."
    )
    parser.add_argument("--evaluation-run", required=True, type=Path)
    parser.add_argument("--quality-store", type=Path, default=Path("./data/model-quality.json"))
    parser.add_argument("--alpha", type=float, default=0.25)
    parser.add_argument("--prior-quality", type=float, default=0.5)
    parser.add_argument("--confidence-full-at", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if not args.evaluation_run.is_file():
            raise ValueError(f"evaluation run does not exist: {args.evaluation_run}")
        if args.quality_store.resolve() == args.evaluation_run.resolve():
            raise ValueError("quality store path must not overwrite the evaluation run")

        run = load_evaluation_run(args.evaluation_run)
        store = JsonFileQualityProfileStore(args.quality_store)
        intelligence = ModelQualityIntelligence(
            policy=QualityLearningPolicy(
                alpha=args.alpha,
                prior_score=args.prior_quality,
                confidence_full_at=args.confidence_full_at,
            ),
            profile_store=store,
        )
        observations = intelligence.ingest_run(run)
        profiles = store.all()
        result = {
            "schema_version": 1,
            "evaluation_run_id": str(run.id),
            "evaluation_run_started_at": run.started_at.isoformat(),
            "quality_store_path": str(args.quality_store),
            "input_result_count": len(run.results),
            "ingested_observation_count": len(observations),
            "skipped_result_count": len(run.results) - len(observations),
            "profile_count": len(profiles),
            "quality_profiles_updated": bool(observations),
            "warning": (
                "Profiles use ingestion timestamps. Freeze this store before a future benchmark; "
                "do not use profiles updated from the target benchmark as its own features."
            ),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if observations else 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
