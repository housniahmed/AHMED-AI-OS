"""FastAPI entry point for AHMED AI OS."""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from core.business.repository import InMemoryBusinessRepository
from core.business.services import BusinessOS
from core.identity.models import UserIdentity
from core.identity.service import UserContextService

app = FastAPI(title="AHMED AI OS API", version="0.1.0", description="API boundary for the personal AI operating system.")
identity_service = UserContextService()
business_os = BusinessOS(InMemoryBusinessRepository())

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
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

@app.get("/health", response_model=HealthResponse, tags=["system"])
def health():
    return HealthResponse(status="ok", service="ahmed-ai-os-api", version=app.version)

@app.post("/v1/users", response_model=UserResponse, status_code=201, tags=["identity"])
def create_user(request: UserCreateRequest):
    try:
        identity = UserIdentity(user_id=uuid4(), display_name=request.display_name, email=request.email, timezone=request.timezone, locale=request.locale)
        record = identity_service.create(identity)
        i = record.identity
        return UserResponse(user_id=i.user_id, display_name=i.display_name, email=i.email, status=i.status.value, timezone=i.timezone, locale=i.locale)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/v1/users/{user_id}/context", tags=["identity"])
def get_context(user_id: UUID):
    try: return identity_service.snapshot(user_id)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc

@app.patch("/v1/users/{user_id}/profile", tags=["identity"])
def update_profile(user_id: UUID, request: ContextUpdateRequest):
    try: return identity_service.update_profile(user_id, request.values)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc

@app.get("/v1/business/snapshot", tags=["business"])
def business_snapshot(): return business_os.snapshot()
