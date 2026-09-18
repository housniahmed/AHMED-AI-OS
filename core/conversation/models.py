"""Provider-neutral conversation domain models."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class MessageRole(str, Enum):
    USER="user"; ASSISTANT="assistant"; SYSTEM="system"
class ConversationStatus(str, Enum):
    ACTIVE="active"; ARCHIVED="archived"

@dataclass(frozen=True, slots=True)
class Message:
    role: MessageRole
    content: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.content.strip(): raise ValueError("Message content must not be empty.")

@dataclass(slots=True)
class Conversation:
    user_id: UUID
    title: str = "New conversation"
    id: UUID = field(default_factory=uuid4)
    status: ConversationStatus = ConversationStatus.ACTIVE
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class ConversationReply:
    conversation_id: UUID
    message: Message
    provider_configured: bool
    status: str
