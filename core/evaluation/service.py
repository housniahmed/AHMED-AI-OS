"""Evaluation framework with injectable metrics and no hidden quality claims."""
from __future__ import annotations
from abc import ABC,abstractmethod
from dataclasses import dataclass
from typing import Any,Callable,Iterable
from .models import EvaluationCase,EvaluationResult,EvaluationRun,EvaluationStatus,MetricResult
class EvaluationMetric(ABC):
    name="metric"
    @abstractmethod
    def score(self,case:EvaluationCase,output:Any)->MetricResult: ...
@dataclass(frozen=True,slots=True)
class CallableMetric(EvaluationMetric):
    name:str; function:Callable[[EvaluationCase,Any],float]; threshold:float|None=None
    def score(self,case,output):
        value=float(self.function(case,output)); passed=self.threshold is None or value>=self.threshold
        return MetricResult(self.name,max(0,min(1,value)),passed,self.threshold)
class DeterministicEvaluator:
    def __init__(self,metrics:Iterable[EvaluationMetric]): self.metrics=tuple(metrics)
    def evaluate(self,case,output,*,duration_ms=None):
        results=tuple(m.score(case,output) for m in self.metrics)
        status=EvaluationStatus.PASSED if all(x.passed for x in results) else EvaluationStatus.FAILED
        return EvaluationResult(case.id,status,results,output,duration_ms=duration_ms)
class EvaluationFramework:
    def __init__(self,evaluator:DeterministicEvaluator): self.evaluator=evaluator
    def run(self,cases:Iterable[EvaluationCase],runner:Callable[[EvaluationCase],Any])->EvaluationRun:
        run=EvaluationRun(); results=[]
        for case in cases:
            try: results.append(self.evaluator.evaluate(case,runner(case)))
            except Exception as exc: results.append(EvaluationResult(case.id,EvaluationStatus.ERROR,error=str(exc)))
        return EvaluationRun(id=run.id,started_at=run.started_at,results=tuple(results))
    @staticmethod
    def summary(run):
        total=len(run.results); passed=sum(r.status is EvaluationStatus.PASSED for r in run.results); failed=sum(r.status is EvaluationStatus.FAILED for r in run.results); errors=sum(r.status is EvaluationStatus.ERROR for r in run.results)
        return {"total":total,"passed":passed,"failed":failed,"errors":errors,"pass_rate":passed/total if total else 0.0}
