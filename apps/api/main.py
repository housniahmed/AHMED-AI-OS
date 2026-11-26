"""FastAPI entry point for AHMED AI OS."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import secrets
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from core.governance.models import ApprovalDecision
from core.identity.models import UserIdentity
from core.system.bootstrap import SystemBootstrap
from integrations.model_providers.openai_compatible import build_model_router_from_env

app = FastAPI(title="AHMED AI OS API", version="0.1.0", description="API boundary for the personal AI operating system.")
def build_system():
    identity = None
    mode = os.getenv("AHMED_IDENTITY_BACKEND", "memory")
    if mode == "postgres":
        from core.persistence.connection import PostgresDatabase
        from core.persistence.identity_service import PostgresIdentityService
        identity = PostgresIdentityService(PostgresDatabase.from_env(), UUID(os.environ["AHMED_OWNER_ID"]))
    elif mode != "memory":
        raise ValueError("unknown identity backend")
    retrieval = None
    memory_mode = os.getenv("AHMED_MEMORY_BACKEND", "disabled")
    if memory_mode == "postgres":
        if mode != "postgres":
            raise ValueError("persistent memory requires persistent identity")
        from core.persistence.memory_service import PersistentMemoryService, PostgresMemoryRetriever
        from core.retrieval.engine import HybridRetrievalEngine
        from core.system.bootstrap import EmptyRetriever
        retrieval = HybridRetrievalEngine(PostgresMemoryRetriever(PersistentMemoryService(identity.database, identity.owner_id)), EmptyRetriever(), EmptyRetriever())
    elif memory_mode != "disabled":
        raise ValueError("unknown memory backend")
    return SystemBootstrap(identity=identity, retrieval=retrieval, model_router=build_model_router_from_env()).build()

system = build_system()
identity_service = system.identity
business_os = system.business
conversation_service = system.conversations
observability = system.observability
security_service = system.security
governance_service = system.governance


bearer = HTTPBearer(auto_error=False)

def authenticated_owner(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> UUID:
    token = os.getenv("AHMED_API_TOKEN", "")
    owner = os.getenv("AHMED_OWNER_ID", "")
    if len(token) < 32 or not owner:
        raise HTTPException(503, "API authentication not configured")
    if credentials is None or not secrets.compare_digest(credentials.credentials.encode(), token.encode()):
        raise HTTPException(401, "Authentication required")
    try:
        return UUID(owner)
    except ValueError:
        raise HTTPException(503, "API owner not configured")

def require_owner(user_id: UUID, owner: UUID):
    if user_id != owner:
        raise HTTPException(403, "Resource access denied")

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    system_composed: bool


class UserCreateRequest(BaseModel):
    display_name: str = ""
    email: str | None = None
    timezone: str = "UTC"
    locale: str = "en-US"


class UserResponse(BaseModel):
    user_id: UUID
    display_name: str
    email: str | None
    status: str
    timezone: str
    locale: str


class ContextUpdateRequest(BaseModel):
    values: dict = Field(default_factory=dict)


class ConversationCreateRequest(BaseModel):
    user_id: UUID
    title: str = "New conversation"


class ConversationResponse(BaseModel):
    conversation_id: UUID
    user_id: UUID
    title: str
    status: str
    message_count: int


class MessageRequest(BaseModel):
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    conversation_id: UUID
    role: str
    content: str
    provider_configured: bool
    status: str


class ApprovalResponse(BaseModel):
    request_id: UUID
    decision: str
    reason: str
    approver_id: UUID | None = None
    action: dict | None = None


class ApprovalInput(BaseModel):
    decision: ApprovalDecision
    approver_id: UUID
    reason: str = ""


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health():
    return HealthResponse(status="ok", service="ahmed-ai-os-api", version=app.version, system_composed=True)


@app.post("/v1/users", response_model=UserResponse, status_code=201, tags=["identity"])
def create_user(request: UserCreateRequest, owner: UUID = Depends(authenticated_owner)):
    try:
        identity = UserIdentity(
            user_id=owner, display_name=request.display_name, email=request.email,
            timezone=request.timezone, locale=request.locale,
        )
        i = identity_service.create(identity).identity
        return UserResponse(
            user_id=i.user_id, display_name=i.display_name, email=i.email,
            status=i.status.value, timezone=i.timezone, locale=i.locale,
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/users/{user_id}/context", tags=["identity"])
def get_context(user_id: UUID, owner: UUID = Depends(authenticated_owner)):
    require_owner(user_id, owner)
    try:
        return identity_service.snapshot(user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.patch("/v1/users/{user_id}/profile", tags=["identity"])
def update_profile(user_id: UUID, request: ContextUpdateRequest, owner: UUID = Depends(authenticated_owner)):
    require_owner(user_id, owner)
    try:
        return identity_service.update_profile(user_id, request.values)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/v1/business/snapshot", tags=["business"])
def business_snapshot(owner: UUID = Depends(authenticated_owner)):
    return business_os.snapshot()


@app.post("/v1/conversations", response_model=ConversationResponse, status_code=201, tags=["conversation"])
def create_conversation(request: ConversationCreateRequest, owner: UUID = Depends(authenticated_owner)):
    require_owner(request.user_id, owner)
    try:
        c = conversation_service.create(request.user_id, request.title)
        return ConversationResponse(
            conversation_id=c.id, user_id=c.user_id, title=c.title,
            status=c.status.value, message_count=0,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/conversations/{conversation_id}", response_model=ConversationResponse, tags=["conversation"])
def get_conversation(conversation_id: UUID, owner: UUID = Depends(authenticated_owner)):
    try:
        c = conversation_service.get(conversation_id)
        require_owner(c.user_id, owner)
        return ConversationResponse(
            conversation_id=c.id, user_id=c.user_id, title=c.title,
            status=c.status.value, message_count=len(c.messages),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/conversations/{conversation_id}/messages", tags=["conversation"])
def get_messages(conversation_id: UUID, owner: UUID = Depends(authenticated_owner)):
    try:
        require_owner(conversation_service.get(conversation_id).user_id, owner)
        return conversation_service.history(conversation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/conversations/{conversation_id}/messages", response_model=MessageResponse, tags=["conversation"])
def send_message(conversation_id: UUID, request: MessageRequest, owner: UUID = Depends(authenticated_owner)):
    trace = observability.start_trace()
    try:
        require_owner(conversation_service.get(conversation_id).user_id, owner)
        r = conversation_service.send(conversation_id, request.content)
        observability.end_trace(trace, success=True)
        return MessageResponse(
            conversation_id=r.conversation_id, role=r.message.role.value,
            content=r.message.content, provider_configured=r.provider_configured,
            status=r.status,
        )
    except KeyError as exc:
        observability.end_trace(trace, success=False)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        observability.end_trace(trace, success=False)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        observability.end_trace(trace, success=False)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/v1/governance/requests/{request_id}", response_model=ApprovalResponse, tags=["governance"])
def get_approval(request_id: UUID, owner: UUID = Depends(authenticated_owner)):
    try:
        req = governance_service.get_request(request_id)
        require_owner(req.user_id, owner)
        d = governance_service.latest(request_id)
        return ApprovalResponse(
            request_id=req.id, decision=d.decision.value,
            reason=d.reason, approver_id=d.approver_id,
            action={"name": req.action.name, "arguments": req.action.arguments, "level": req.action.action_level, "resource": req.action.resource},
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/governance/requests/{request_id}/decision", response_model=ApprovalResponse, tags=["governance"])
def decide_approval(request_id: UUID, input: ApprovalInput, owner: UUID = Depends(authenticated_owner)):
    try:
        require_owner(governance_service.get_request(request_id).user_id, owner)
        require_owner(input.approver_id, owner)
        d = governance_service.decide(request_id, input.decision, owner, reason=input.reason)
        return ApprovalResponse(
            request_id=d.request_id, decision=d.decision.value,
            reason=d.reason, approver_id=d.approver_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/v1/governance/requests/{request_id}/resume", tags=["governance"])
def resume_approval(request_id: UUID, owner: UUID = Depends(authenticated_owner)):
    try:
        require_owner(governance_service.get_request(request_id).user_id, owner)
        result = system.gateway.resume(request_id, owner)
        if not result.result.success:
            raise HTTPException(409, "Execution denied or failed; do not retry automatically")
        return {"request_id": request_id, "status": "completed", "output": result.result.output}
    except KeyError as exc:
        raise HTTPException(404, "Approval not found") from exc
    except PermissionError as exc:
        raise HTTPException(403, "Access denied") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/ready", tags=["system"])
def readiness():
    from core.persistence.connection import PostgresDatabase
    try:
        UUID(os.environ["AHMED_OWNER_ID"])
        if len(os.environ.get("AHMED_API_TOKEN", "")) < 32:
            raise ValueError("authentication missing")
        if not PostgresDatabase.from_env().check():
            raise RuntimeError("database unavailable")
    except Exception:
        raise HTTPException(503, "Infrastructure not ready")
    # Persistent services are not wired yet: never advertise production readiness.
    return {"status": "staging", "database_connected": True,
            "production_ready": False, "storage": "mixed" if os.getenv("AHMED_IDENTITY_BACKEND") == "postgres" else "in-memory application services"}
