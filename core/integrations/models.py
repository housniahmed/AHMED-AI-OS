"""Domain models for external integrations. No provider SDKs are imported here."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

@dataclass(frozen=True, slots=True)
class CalendarEvent:
    title: str
    start_at: datetime
    end_at: datetime
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    location: str = ""
    attendees: tuple[str, ...] = ()
    external_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if not self.title.strip(): raise ValueError("calendar event title cannot be empty")
        if self.end_at <= self.start_at: raise ValueError("calendar event end must be after start")

@dataclass(frozen=True, slots=True)
class EmailMessage:
    subject: str
    sender: str
    recipients: tuple[str, ...]
    id: UUID = field(default_factory=uuid4)
    body: str = ""
    thread_id: str | None = None
    external_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if not self.subject.strip(): raise ValueError("email subject cannot be empty")
        if not self.recipients: raise ValueError("email requires at least one recipient")

@dataclass(frozen=True, slots=True)
class TelegramMessage:
    chat_id: str
    text: str
    id: UUID = field(default_factory=uuid4)
    external_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if not self.chat_id.strip(): raise ValueError("telegram chat_id cannot be empty")
        if not self.text.strip(): raise ValueError("telegram text cannot be empty")
