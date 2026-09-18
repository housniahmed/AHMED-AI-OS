from datetime import datetime, timedelta, timezone

from core.temporal.intelligence import TemporalIntelligence
from core.temporal.models import Event, EventType, TemporalRelation
from core.temporal.timeline import Timeline


BASE = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)


def test_timeline_orders_and_queries_intervals():
    timeline = Timeline()
    early = timeline.add(Event("early", EventType.TASK, BASE))
    later = timeline.add(Event("later", EventType.MEETING, BASE + timedelta(hours=2)))
    assert timeline.all() == (early, later)
    assert timeline.between(BASE, BASE + timedelta(hours=1)) == (early,)


def test_temporal_relation_before():
    timeline = Timeline()
    a = Event("a", EventType.TASK, BASE)
    b = Event("b", EventType.MEETING, BASE + timedelta(hours=1))
    assert timeline.relation(a, b) == TemporalRelation.BEFORE


def test_overdue_deadline_is_detected():
    timeline = Timeline()
    timeline.add(Event("deadline", EventType.DEADLINE, BASE - timedelta(days=1)))
    intelligence = TemporalIntelligence(timeline)
    assert len(intelligence.overdue(BASE)) == 1
