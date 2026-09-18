"""Deterministic scheduler; it decides when a workflow is eligible to run."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Iterable
from uuid import UUID
from .models import ScheduleDefinition, ScheduleRun, ScheduleState, TriggerType

class SchedulerStore(ABC):
    @abstractmethod
    def save_schedule(self, schedule: ScheduleDefinition, state: ScheduleState = ScheduleState.ACTIVE) -> None: raise NotImplementedError
    @abstractmethod
    def get_schedule(self, schedule_id: UUID) -> tuple[ScheduleDefinition, ScheduleState]: raise NotImplementedError
    @abstractmethod
    def save_run(self, run: ScheduleRun) -> ScheduleRun: raise NotImplementedError
    @abstractmethod
    def list_schedules(self) -> Iterable[tuple[ScheduleDefinition, ScheduleState]]: raise NotImplementedError

class InMemorySchedulerStore(SchedulerStore):
    def __init__(self) -> None: self._schedules={}; self._runs={}
    def save_schedule(self,schedule,state=ScheduleState.ACTIVE): self._schedules[schedule.id]=(schedule,state)
    def get_schedule(self,schedule_id): return self._schedules[schedule_id]
    def save_run(self,run): self._runs[run.id]=run; return run
    def list_schedules(self): return tuple(self._schedules.values())

class Scheduler:
    def __init__(self, store: SchedulerStore | None = None) -> None: self.store=store or InMemorySchedulerStore()
    def register(self, schedule: ScheduleDefinition) -> ScheduleDefinition:
        self.store.save_schedule(schedule); return schedule
    def pause(self, schedule_id: UUID) -> None:
        schedule,_=self.store.get_schedule(schedule_id); self.store.save_schedule(schedule,ScheduleState.PAUSED)
    def cancel(self, schedule_id: UUID) -> None:
        schedule,_=self.store.get_schedule(schedule_id); self.store.save_schedule(schedule,ScheduleState.CANCELLED)
    def due(self, now: datetime | None = None) -> tuple[ScheduleDefinition,...]:
        now=now or datetime.now(timezone.utc)
        result=[]
        for schedule,state in self.store.list_schedules():
            if state is not ScheduleState.ACTIVE: continue
            if schedule.trigger_type is TriggerType.TIME and schedule.kind.value=="once" and schedule.run_at and schedule.run_at <= now: result.append(schedule)
            elif schedule.trigger_type is TriggerType.TIME and schedule.kind.value=="interval" and schedule.run_at and schedule.run_at <= now: result.append(schedule)
        return tuple(result)
    def emit_event(self, event_name: str) -> tuple[ScheduleDefinition,...]:
        return tuple(s for s,state in self.store.list_schedules() if state is ScheduleState.ACTIVE and s.trigger_type is TriggerType.EVENT and s.event_name==event_name)
    def check_condition(self, condition: str) -> tuple[ScheduleDefinition,...]:
        return tuple(s for s,state in self.store.list_schedules() if state is ScheduleState.ACTIVE and s.trigger_type is TriggerType.CONDITION and s.condition==condition)
