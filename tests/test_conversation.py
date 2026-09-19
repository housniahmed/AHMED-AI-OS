from uuid import uuid4
import pytest
from core.conversation.models import Message,MessageRole
from core.conversation.service import ConversationService,ConversationProvider,OrchestratorConversationProvider

def test_create_and_history():
    s=ConversationService(); c=s.create(uuid4(),"Research"); result=s.send(c.id,"Hello")
    assert not result.provider_configured; assert s.history(c.id)[0].role is MessageRole.USER

def test_empty_message_rejected():
    with pytest.raises(ValueError): Message(role=MessageRole.USER,content=" ")

class StubProvider(ConversationProvider):
    def respond(self,conversation,user_message): return "Stub response"

def test_provider_reply():
    s=ConversationService(StubProvider()); c=s.create(uuid4()); result=s.send(c.id,"Question")
    assert result.provider_configured; assert result.message.role is MessageRole.ASSISTANT

class StubOrchestrator:
    def __init__(self,result): self.result=result; self.requests=[]
    def run(self,request): self.requests.append(request); return self.result

def test_conversation_to_orchestrator():
    from core.agent.models import AgentState,AgentPhase
    from core.orchestration.models import OrchestrationState,OrchestrationResult
    user=uuid4(); c=ConversationService(OrchestratorConversationProvider(
        StubOrchestrator(OrchestrationResult(
            request=None,state=OrchestrationState.COMPLETED,user_context=None,
            agent_state=AgentState("hello",phase=AgentPhase.COMPLETE,result="orchestrated")
        ))
    )).create(user)
    result=service.send(c.id,"hello")
    assert result.message.content=="orchestrated"
    assert result.provider_configured
    assert orchestrator.requests[0].user_id==user
