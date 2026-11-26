from uuid import uuid4
from core.conversation.service import ConversationService, OrchestratorConversationProvider
from core.system.bootstrap import SystemBootstrap
from core.identity.models import UserIdentity
from core.agent.models import AgentAction
from core.intelligence.planner import ModelAgentPlanner

class Planner:
    def __init__(self):
        self.context=None
        self.propose=False
    def infer(self,request,context):
        self.context=context
        return ("answer",), ((AgentAction("probe","test","read"),) if self.propose else ())

def test_history_reaches_planner_and_blocks_actions():
    import pytest
    owner=uuid4()
    planner=Planner()
    system=SystemBootstrap(planner=planner).build()
    system.identity.create(UserIdentity(user_id=owner,display_name="CI"))
    c=system.conversations.create(owner)
    system.conversations.send(c.id,"first")
    reply=system.conversations.send(c.id,"second")
    assert reply.message.content=="answer"
    assert planner.context.conversation_history==(("user","first"),("assistant","answer"))
    assert ModelAgentPlanner._context_payload(planner.context)["conversation_history"][0]=={"role":"user","content":"first"}
    planner.propose=True
    with pytest.raises(RuntimeError):
        system.conversations.send(c.id,"third")

def test_history_window_limit():
    from core.orchestration.models import OrchestrationResult, OrchestrationState
    class Capture:
        def run(self,request):
            self.request=request
            return OrchestrationResult(request,OrchestrationState.COMPLETED,None)
    capture=Capture()
    service=ConversationService(OrchestratorConversationProvider(capture))
    c=service.create(uuid4())
    for i in range(15):
        service.send(c.id,str(i))
    assert len(capture.request.conversation_history)==20
    assert capture.request.text=="14"
