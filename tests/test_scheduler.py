from datetime import datetime, timedelta, timezone
from uuid import uuid4
from core.scheduler.models import ScheduleDefinition, ScheduleKind, TriggerType, ScheduleState
from core.scheduler.scheduler import Scheduler

def test_due_once_schedule():
    now=datetime.now(timezone.utc)
    s=ScheduleDefinition("daily",TriggerType.TIME,uuid4(),kind=ScheduleKind.ONCE,run_at=now-timedelta(minutes=1))
    assert Scheduler().due(now)==(s,)

def test_interval_must_not_be_faster_than_hour():
    try:
        ScheduleDefinition("fast",TriggerType.TIME,uuid4(),kind=ScheduleKind.INTERVAL,interval_seconds=3599,run_at=datetime.now(timezone.utc))
        assert False
    except ValueError: pass

def test_event_trigger():
    s=ScheduleDefinition("on push",TriggerType.EVENT,uuid4(),event_name="github.push")
    assert Scheduler().emit_event("github.push")==()
    sch=Scheduler(); sch.register(s)
    assert sch.emit_event("github.push")== (s,)

def test_pause_removes_schedule_from_due():
    now=datetime.now(timezone.utc)
    s=ScheduleDefinition("once",TriggerType.TIME,uuid4(),run_at=now-timedelta(seconds=1))
    sch=Scheduler(); sch.register(s); sch.pause(s.id)
    assert sch.due(now)==()
