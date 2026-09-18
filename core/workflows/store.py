"""Persistence contract for workflow runs."""
from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID
from .models import WorkflowRun

class WorkflowStore(ABC):
    @abstractmethod
    def save(self, run: WorkflowRun) -> WorkflowRun: raise NotImplementedError
    @abstractmethod
    def get(self, run_id: UUID) -> WorkflowRun: raise NotImplementedError

class InMemoryWorkflowStore(WorkflowStore):
    def __init__(self) -> None: self._runs = {}
    def save(self, run: WorkflowRun) -> WorkflowRun:
        self._runs[run.id] = run
        return run
    def get(self, run_id: UUID) -> WorkflowRun:
        try: return self._runs[run_id]
        except KeyError: raise KeyError(f"workflow run not found: {run_id}") from None
