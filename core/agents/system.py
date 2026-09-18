"""Deterministic multi-agent coordination without vendor-specific SDKs."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Iterable
from .models import AgentExecutionState, AgentResult, AgentTask, MultiAgentPlan

class AgentWorker(ABC):
    @abstractmethod
    def run(self, task: AgentTask, dependency_results: tuple[AgentResult, ...]) -> AgentResult:
        raise NotImplementedError

class AgentSelector(ABC):
    @abstractmethod
    def select(self, task: AgentTask) -> AgentWorker:
        raise NotImplementedError

class MultiAgentSystem:
    def __init__(self, selector: AgentSelector) -> None:
        self.selector = selector
    def execute(self, plan: MultiAgentPlan) -> tuple[AgentResult, ...]:
        ordered = plan.topological_order()
        results = {}
        for task in ordered:
            dependencies = tuple(results[i] for i in task.dependency_ids)
            if any(r.state is not AgentExecutionState.COMPLETED for r in dependencies):
                result = AgentResult(task.id, AgentExecutionState.BLOCKED, error="A dependency did not complete successfully.")
            else:
                try:
                    result = self.selector.select(task).run(task, dependencies)
                    if result.task_id != task.id:
                        raise ValueError("agent worker returned a result for a different task")
                except Exception as exc:
                    result = AgentResult(task.id, AgentExecutionState.FAILED, error=str(exc))
            results[task.id] = result
        return tuple(results[t.id] for t in ordered)
    @staticmethod
    def aggregate(results: Iterable[AgentResult]) -> dict[str, Any]:
        items = tuple(results)
        return {"total": len(items), "completed": sum(r.state is AgentExecutionState.COMPLETED for r in items), "failed": sum(r.state is AgentExecutionState.FAILED for r in items), "blocked": sum(r.state is AgentExecutionState.BLOCKED for r in items), "outputs": tuple(r.output for r in items if r.state is AgentExecutionState.COMPLETED)}
