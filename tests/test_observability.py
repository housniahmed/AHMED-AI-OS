from core.observability.models import AuditEvent, EventKind
from core.observability.service import InMemoryObservabilitySink, ObservabilityService

def test_trace_and_span_context():
    sink=InMemoryObservabilitySink(); obs=ObservabilityService(sink); root=obs.start_trace(); child=obs.span(root)
    assert child.trace_id==root.trace_id; assert child.parent_span_id==root.span_id
    obs.end_trace(root,success=True,duration_ms=12.5); assert len(sink.events)==2; assert sink.events[-1].kind is EventKind.TRACE_COMPLETED

def test_events_and_metrics_are_recorded():
    sink=InMemoryObservabilitySink(); obs=ObservabilityService(sink); trace=obs.start_trace()
    obs.emit(AuditEvent(EventKind.TOOL,"tool.execute",obs.span(trace),success=True)); obs.metric("tool.duration_ms",42,{"tool":"demo"})
    assert len(sink.events)==2; assert sink.metrics[-1].value==42.0
