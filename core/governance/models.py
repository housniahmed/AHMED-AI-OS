"""Human approval and governance domain models."""
from __future__ import annotations
from dataclasses import dataclass,field
from enum import Enum
from typing import Any
from uuid import UUID,uuid4
class RiskLevel(int,Enum): LOW=1; MEDIUM=2; HIGH=3; CRITICAL=4
class ApprovalScope(str,Enum): ACTION="action"; RESOURCE="resource"; WORKFLOW="workflow"
class ApprovalDecision(str,Enum): PENDING="pending"; APPROVED="approved"; REJECTED="rejected"; EXPIRED="expired"
@dataclass(frozen=True,slots=True)
class GovernanceAction:
    name:str; resource:str; risk:RiskLevel=RiskLevel.MEDIUM; arguments:dict[str,Any]=field(default_factory=dict); id:UUID=field(default_factory=uuid4)
@dataclass(frozen=True,slots=True)
class ApprovalRequest:
    action:GovernanceAction; user_id:UUID; scope:ApprovalScope=ApprovalScope.ACTION; id:UUID=field(default_factory=uuid4)
@dataclass(frozen=True,slots=True)
class GovernanceDecision:
    request_id:UUID; decision:ApprovalDecision; reason:str; approver_id:UUID|None=None
