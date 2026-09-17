from datetime import datetime, timedelta, timezone

from core.domain.models import Memory, MemoryType, Provenance
from core.memory.consolidation import MemoryConsolidator
from core.memory.lifecycle import MemoryLifecycle, MemoryOperation


def make_memory(content, updated_at=None):
    return Memory(content, MemoryType.SEMANTIC, Provenance("test", "1"), updated_at=updated_at or datetime.now(timezone.utc))


def test_expired_memory_is_archived():
    memory = make_memory("old", datetime.now(timezone.utc) - timedelta(days=10))
    memory.valid_until = datetime.now(timezone.utc) - timedelta(days=1)
    decisions = MemoryLifecycle().plan([memory])
    assert decisions[0].operation == MemoryOperation.ARCHIVE


def test_stale_memory_is_marked_for_decay():
    memory = make_memory("old", datetime.now(timezone.utc) - timedelta(days=200))
    decisions = MemoryLifecycle(stale_after_days=180).plan([memory])
    assert decisions[0].operation == MemoryOperation.DECAY


def test_exact_duplicates_are_detected_without_deletion():
    a = make_memory("Important decision")
    b = make_memory("  important   decision ")
    candidates = MemoryConsolidator().find_exact_duplicates([a, b])
    assert len(candidates) == 1
    assert candidates[0].primary_id == a.id
    assert candidates[0].duplicate_ids == (b.id,)
