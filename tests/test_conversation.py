from uuid import uuid4
import pytest
from core.conversation.models import Message, MessageRole
from core.conversation.service import ConversationService, ConversationProvider

def test_create_and_history():
    s=ConversationService(); c=s.create(uuid4(),"Research")
    result=s.send(c.id,"Hello")
    assert result.provider_configured is False
    assert s.history(c.id)[0].role is MessageRole.USER

def test_empty_message_rejected():
    with pytest.raises(ValueError): Message(role=MessageRole.USER,content=" ")

class StubProvider(ConversationProvider):
    def respond(self, conversation, user_message): return "Stub response"

def test_provider_reply():
    s=ConversationService(StubProvider()); c=s.create(uuid4())
    result=s.send(c.id,"Question")
    assert result.provider_configured is True
    assert result.message.role is MessageRole.ASSISTANT
