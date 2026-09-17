from core.domain.models import MemoryType, Sensitivity
from core.memory.repository import InMemoryRepository
from core.memory.service import MemoryService


def test_remember_preserves_provenance() -> None:
    service = MemoryService(InMemoryRepository())
    memory = service.remember(
        "Use verified sources for scientific claims.",
        MemoryType.PROCEDURAL,
        "user_instruction",
        "conversation:current",
        sensitivity=Sensitivity.RESTRICTED,
        confidence=1.0,
        tags=["research", "integrity"],
    )

    assert memory.content == "Use verified sources for scientific claims."
    assert memory.provenance.source_type == "user_instruction"
    assert memory.provenance.source_id == "conversation:current"
    assert memory.sensitivity is Sensitivity.RESTRICTED
    assert memory.confidence == 1.0


def test_empty_memory_is_rejected() -> None:
    service = MemoryService(InMemoryRepository())

    try:
        service.remember("   ", MemoryType.SEMANTIC, "test", "1")
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("Expected empty memory to be rejected")


def test_invalid_confidence_is_rejected() -> None:
    service = MemoryService(InMemoryRepository())

    try:
        service.remember("fact", MemoryType.SEMANTIC, "test", "1", confidence=1.1)
    except ValueError as exc:
        assert "confidence" in str(exc)
    else:
        raise AssertionError("Expected invalid confidence to be rejected")
