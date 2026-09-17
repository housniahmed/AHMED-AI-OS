"""Deterministic text chunking with stable character offsets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    content: str
    char_start: int
    char_end: int


def chunk_text(text: str, *, chunk_size: int = 1200, overlap: int = 200) -> list[TextChunk]:
    """Split text into bounded chunks while preserving source offsets.

    The algorithm prefers whitespace boundaries. It is deliberately deterministic
    so the same source produces the same chunk boundaries across runs.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    normalized = text.strip()
    if not normalized:
        return []

    chunks: list[TextChunk] = []
    start = 0
    length = len(normalized)

    while start < length:
        target_end = min(start + chunk_size, length)
        end = target_end

        if target_end < length:
            boundary = normalized.rfind(" ", start, target_end)
            if boundary > start + chunk_size // 2:
                end = boundary

        content = normalized[start:end].strip()
        if content:
            actual_start = start + len(normalized[start:end]) - len(normalized[start:end].lstrip())
            actual_end = actual_start + len(content)
            chunks.append(TextChunk(content, actual_start, actual_end))

        if end >= length:
            break

        next_start = max(0, end - overlap)
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks
