"""Deterministic workflow execution engine with checkpoints and resumability."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Any
from uuid import UUID
from .models import StepResult, StepState, WorkflowDefinition, WorkflowRun, WorkflowState, WorkflowStep
from .store import WorkflowStore, InMemoryWorkflowStore

class WorkflowStepExecutor(ABC):
    @abstractmethod
    def execute(self, step: WorkflowStep, input_data: Any, dependency_outputs: dict[UUID, Any]) -> StepResult:
        raise NotImplementedError

class WorkflowEngine:
    """Execute a workflow DAG while persisting state after each checkpoint."""
    def __init__(self, executor: WorkflowStepExecutor, store: WorkflowStore | None = None) -> None:
        self.executor = executor
        self.store = store or InMemoryWorkflowStore()

    def start(self, workflow: WorkflowDefinition, input_data: Any = None) -> WorkflowRun:
        states = {s.id: StepState.PENDING for s in workflow.steps}
        run = WorkflowRun(workflow.id, input_data=input_data, step_states=states, checkpoint="created")
        return self.store.save(run)

    def run(self, workflow: WorkflowDefinition, run_id: UUID | None = None, input_data: Any = None) -> WorkflowRun:
        run = self.start(workflow, input_data) if run_id is None else self.store.get(run_id)
        if run.workflow_id != workflow.id: raise ValueError("workflow definition does not match run")
        if run.state in (WorkflowState.COMPLETED, WorkflowState.CANCELLED): return run
        run = self._save(replace(run, state=WorkflowState.RUNNING, checkpoint="started"))
        for step in workflow.topological_order():
            current = self.store.get(run.id)
            if current.step_states.get(step.id) is StepState.COMPLETED: continue
            if any(current.step_states[d] is not StepState.COMPLETED for d in step.dependency_ids):
                current = self._save(replace(current, state=WorkflowState.FAILED, current_step_id=step.id, checkpoint="blocked", errors={**current.errors, step.id:"dependency not completed"}))
                return current
            current = self._save(replace(current, current_step_id=step.id, checkpoint=f"before:{step.id}", step_states={**current.step_states, step.id:StepState.RUNNING}))
            try:
                result = self.executor.execute(step, current.input_data, {d: current.outputs[d] for d in step.dependency_ids})
                if result.step_id != step.id: raise ValueError("executor returned a result for a different step")
                if result.state is not StepState.COMPLETED:
                    state = WorkflowState.WAITING if result.state is StepState.FAILED and step.metadata.get("wait_on_failure") else WorkflowState.FAILED
                    errors = {**current.errors, step.id: result.error or "step did not complete"}
                    current = self._save(replace(current, state=state, checkpoint=f"after:{step.id}", step_states={**current.step_states, step.id:result.state}, errors=errors))
                    return current
                current = self._save(replace(current, step_states={**current.step_states, step.id:StepState.COMPLETED}, outputs={**current.outputs, step.id:result.output}, checkpoint=f"after:{step.id}"))
            except Exception as exc:
                current = self._save(replace(current, state=WorkflowState.FAILED, checkpoint=f"error:{step.id}", step_states={**current.step_states, step.id:StepState.FAILED}, errors={**current.errors, step.id:str(exc)}))
                return current
        return self._save(replace(self.store.get(run.id), state=WorkflowState.COMPLETED, current_step_id=None, checkpoint="completed"))

    def resume(self, workflow: WorkflowDefinition, run_id: UUID) -> WorkflowRun:
        return self.run(workflow, run_id=run_id)

    def cancel(self, run_id: UUID) -> WorkflowRun:
        run = self.store.get(run_id)
        return self._save(replace(run, state=WorkflowState.CANCELLED, checkpoint="cancelled"))

    def _save(self, run: WorkflowRun) -> WorkflowRun:
        return self.store.save(run)
