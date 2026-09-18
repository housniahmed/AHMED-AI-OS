"""Provider-neutral security models."""
from __future__ import annotations
from dataclasses import dataclass,field
from enum import Enum
from typing import Any
from uuid import UUID,uuid4
class AccessLevel(int,Enum): NONE=0; READ=1; WRITE=2; EXECUTE=3; ADMIN=4
@dataclass(frozen=True,slots=True)
class SecurityPrincipal:
    user_id:UUID; roles:tuple[str,...]=(); attributes:dict[str,Any]=field(default_factory=dict)
@dataclass(frozen=True,slots=True)
class SecurityAction:
    resource:str; operation:str; required_level:AccessLevel=AccessLevel.READ; id:UUID=field(default_factory=uuid4)
@dataclass(frozen=True,slots=True)
class SecurityDecision:
    allowed:bool; reason:str; principal_id:UUID; action_id:UUID
