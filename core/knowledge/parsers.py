"""Source parsers for the first ingestion milestone.

Binary formats are intentionally handled through explicit adapters rather than
silently guessing how a file should be decoded.
"""

from __future__ import annotations

from pathlib import Path

SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".csv", ".json"}


class UnsupportedDocumentError(ValueError):
    pass


def parse_text_file(path: str | Path) -> str:
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_TEXT_SUFFIXES:
        raise UnsupportedDocumentError(
            f"Unsupported text format: {path.suffix or '<no extension>'}"
        )
    return path.read_text(encoding="utf-8")


def parse_source(path: str | Path) -> str:
    """Parse a supported source without hiding decoding or format failures."""
    path = Path(path)
    if path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES:
        return parse_text_file(path)
    raise UnsupportedDocumentError(
        f"No parser registered for {path.suffix or '<no extension>'}"
    )
