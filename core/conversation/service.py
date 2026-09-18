"""Conversation service. It never executes tools directly."""
from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID
from .models import Conversation, ConversationReply, Message, MessageRole

class ConversationProvider(ABC):
    @abstractmethod
    def respond(self, conversation: Conversation, user_message: Message) -> str: ...

class UnconfiguredConversationProvider(ConversationProvider):
    def respond(self, conversation: Conversation, user_message: Message) -> str:
        raise RuntimeError("No conversation model provider is configured.")

class ConversationService:
    def __init__(self, provider: ConversationProvider | None = None):
        self._provider = provider
        self._conversations: dict[UUID, Conversation] = {}

    def create(self, user_id: UUID, title: str = "New conversation") -> Conversation:
        if not title.strip(): raise ValueError("Conversation title must not be empty.")
        c=Conversation(user_id=user_id,title=title.strip()); self._conversations[c.id]=c; return c

    def get(self, conversation_id: UUID) -> Conversation:
        try: return self._conversations[conversation_id]
        except KeyError as exc: raise KeyError("Conversation not found.") from exc

    def history(self, conversation_id: UUID) -> list[Message]:
        return list(self.get(conversation_id).messages)

    def send(self, conversation_id: UUID, user_message: str) -> ConversationReply:
        c=self.get(conversation_id)
        msg=Message(role=MessageRole.USER, content=user_message)
        c.messages.append(msg)
        c.updated_at=msg.created_at
        if self._provider is None:
            return ConversationReply(conversation_id=c.id, message=msg, provider_configured=False, status="accepted_pending_provider")
        reply_text=self._provider.respond(c,msg)
        reply=Message(role=MessageRole.ASSISTANT,content=reply_text)
        c.messages.append(reply); c.updated_at=reply.created_at
        return ConversationReply(conversation_id=c.id,message=reply,provider_configured=True,status="completed")
