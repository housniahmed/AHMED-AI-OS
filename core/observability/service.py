"""Minimal observability service with injectable sinks."""
from __future__ import annotations
from abc import ABC, abstractmethod
from collections import Counter
from typing import Iterable
from .models import AuditEvent, EventKind, MetricPoint, TraceContext
class ObservabilitySink(ABC):
    @abstractmethod
    def record_event(self,event: AuditEvent)->None: ...
    @abstractmethod
    def record_metric(self,metric: MetricPoint)->None: ...
class InMemoryObservabilitySink(ObservabilitySink):
    def __init__(self): self.events=[]; self.metrics=[]
    def record_event(self,event): self.events.append(event)
    def record_metric(self,metric): self.metrics.append(metric)
class ObservabilityService:
    def __init__(self,sink:ObservabilitySink): self.sink=sink; self._counters=Counter()
    def start_trace(self,*,user_id=None,correlation_id=None):
        trace=TraceContext(); self.emit(AuditEvent(EventKind.TRACE_STARTED,"trace.start",trace,user_id=user_id,correlation_id=correlation_id)); return trace
    def span(self,parent): return TraceContext(trace_id=parent.trace_id,parent_span_id=parent.span_id)
    def emit(self,event): self.sink.record_event(event); self._counters[f"events.{event.kind.value}"]+=1
    def metric(self,name,value,labels=None): self.sink.record_metric(MetricPoint(name=name,value=float(value),labels=labels or {}))
    def count(self,name,increment=1,labels=None): self._counters[name]+=increment; self.metric(name,float(increment),labels)
    def end_trace(self,trace,*,success,duration_ms=None,user_id=None,correlation_id=None):
        kind=EventKind.TRACE_COMPLETED if success else EventKind.TRACE_FAILED; self.emit(AuditEvent(kind,"trace.end",trace,duration_ms=duration_ms,success=success,user_id=user_id,correlation_id=correlation_id))
    def events(self)->Iterable[AuditEvent]: return tuple(self.sink.events) if isinstance(self.sink,InMemoryObservabilitySink) else ()
    def metrics(self)->Iterable[MetricPoint]: return tuple(self.sink.metrics) if isinstance(self.sink,InMemoryObservabilitySink) else ()
