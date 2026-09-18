"""Provider-neutral evaluation domain models."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

def utc_now(): return datetime.now(timezone.utc)
class EvaluationStatus(str,Enum): PENDING="pending"; PASSED="passed"; FAILED="failed"; ERROR="error"
@dataclass(frozen=True,slots=True)
class EvaluationCase:
    name:str; input:Any; expected:Any=None; id:UUID=field(default_factory=uuid4); metadata:dict[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if not self.name.strip(): raise ValueError("Evaluation case name must not be empty.")
@dataclass(frozen=True,slots=True)
class MetricResult:
    name:str; score:float; passed:bool; threshold:float|None=None; details:dict[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if not 0<=self.score<=1: raise ValueError("Metric score must be between 0 and 1.")
        if self.threshold is not None and not 0<=self.threshold<=1: raise ValueError("Metric threshold must be between 0 and 1.")
@dataclass(frozen=True,slots=True)
class EvaluationResult:
    case_id:UUID; status:EvaluationStatus; metrics:tuple[MetricResult,...]=(); output:Any=None; error:str|None=None; duration_ms:float|None=None
@dataclass(frozen=True,slots=True)
class EvaluationRun:
    id:UUID=field(default_factory=uuid4); started_at:datetime=field(default_factory=utc_now); results:tuple[EvaluationResult,...]=()
