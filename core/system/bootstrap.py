"""Dependency composition root for AHMED AI OS.

This module owns wiring. It does not implement an LLM, database, or external
provider; those remain explicit injection points so the system cannot pretend
that an unavailable provider is configured.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from core.agent.runtime import ActionExecutor, AgentPlanner, AgentRuntime
from core.business.repository import InMemoryBusinessRepository
from core.business.services import BusinessOS
from core.context.engine import ContextEngine
from core.conversation.service import ConversationService, OrchestratorConversationProvider
from core.governance.service import GovernanceService, InMemoryGovernanceAuditSink
from core.identity.service import UserContextService
from core.observability.service import ObservabilityService, InMemoryObservabilitySink
from core.orchestration.orchestrator import UnifiedOrchestrator
from core.retrieval.engine import HybridRetrievalEngine, LexicalRetriever, MetadataRetriever, SemanticRetriever
from core.retrieval.models import RetrievalCandidate, RetrievalQuery
from core.security.service import SecurityService, InMemorySecurityAuditSink
from core.tools.gateway import GatewayRequest, ToolExecutionGateway
from core.tools.models import ToolResult
from core.tools.registry import ToolRegistry
from core.tools.runtime import ToolRuntime


class EmptyRetriever(LexicalRetriever, SemanticRetriever, MetadataRetriever):
    """Explicit development retriever used until a real provider is injected."""

    def search(self, query: RetrievalQuery) -> list[RetrievalCandidate]:
        return []


class NoOpPlanner(AgentPlanner):
    """Explicitly non-generative planner for a provider-free bootstrap."""

    def infer(self, request: str, context):
        return ("No model planner is configured; no action was proposed.",), ()


class GatewayActionExecutor(ActionExecutor):
    """Route every agent execution attempt through B17."""

    def __init__(self, gateway: ToolExecutionGateway) -> None:
        self.gateway = gateway

    def execute(self, action):
        raise RuntimeError("GatewayActionExecutor requires a user-scoped execution request.")

    def execute_for_user(self, action, user_id: UUID | None = None) -> ToolResult:
        if user_id is None:
            raise ValueError("user_id is required for gateway execution")
        return self.gateway.execute(GatewayRequest(action=action, user_id=user_id)).result


@dataclass(slots=True)
class SystemContainer:
    identity: UserContextService
    business: BusinessOS
    observability: ObservabilityService
    security: SecurityService
    governance: GovernanceService
    tool_registry: ToolRegistry
    tool_runtime: ToolRuntime
    gateway: ToolExecutionGateway
    retrieval: HybridRetrievalEngine
    context: ContextEngine
    agent: AgentRuntime
    orchestrator: UnifiedOrchestrator
    conversations: ConversationService


class SystemBootstrap:
    """Build one coherent dependency graph for the application process."""

    def __init__(self, *,
                 identity: UserContextService | None = None,
                 business: BusinessOS | None = None,
                 observability: ObservabilityService | None = None,
                 security: SecurityService | None = None,
                 governance: GovernanceService | None = None,
                 retrieval: HybridRetrievalEngine | None = None,
                 context: ContextEngine | None = None,
                 agent: AgentRuntime | None = None,
                 orchestrator: UnifiedOrchestrator | None = None,
                 conversations: ConversationService | None = None) -> None:
        self.identity = identity or UserContextService()
        self.business = business or BusinessOS(InMemoryBusinessRepository())
        self.observability = observability or ObservabilityService(InMemoryObservabilitySink())
        self.security = security or SecurityService(InMemorySecurityAuditSink())
        self.governance = governance or GovernanceService(InMemoryGovernanceAuditSink())
        self._retrieval = retrieval
        self._context = context
        self._agent = agent
        self._orchestrator = orchestrator
        self._conversations = conversations

    def build(self) -> SystemContainer:
        retrieval = self._retrieval or self._default_retrieval()
        context = self._context or ContextEngine()
        registry = ToolRegistry()
        runtime = ToolRuntime(registry)
        gateway = ToolExecutionGateway(runtime, self.security, self.governance)

        agent = self._agent or AgentRuntime(
            retrieval, context, NoOpPlanner(), GatewayActionExecutor(gateway)
        )
        orchestrator = self._orchestrator or UnifiedOrchestrator(self.identity, agent)
        conversations = self._conversations or ConversationService(
            OrchestratorConversationProvider(orchestrator)
        )
        return SystemContainer(
            identity=self.identity,
            business=self.business,
            observability=self.observability,
            security=self.security,
            governance=self.governance,
            tool_registry=registry,
            tool_runtime=runtime,
            gateway=gateway,
            retrieval=retrieval,
            context=context,
            agent=agent,
            orchestrator=orchestrator,
            conversations=conversations,
        )

    @staticmethod
    def _default_retrieval() -> HybridRetrievalEngine:
        provider = EmptyRetriever()
        return HybridRetrievalEngine(provider, provider, provider)
