"""Provider-neutral Business OS models."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

class LeadStatus(str, Enum): NEW="new"; QUALIFIED="qualified"; CONTACTED="contacted"; CONVERTED="converted"; LOST="lost"
class CustomerStatus(str, Enum): PROSPECT="prospect"; ACTIVE="active"; INACTIVE="inactive"
class DealStatus(str, Enum): OPEN="open"; WON="won"; LOST="lost"; CANCELLED="cancelled"
class CampaignStatus(str, Enum): DRAFT="draft"; ACTIVE="active"; PAUSED="paused"; COMPLETED="completed"

@dataclass(frozen=True, slots=True)
class Lead:
    name: str
    id: UUID = field(default_factory=uuid4)
    email: str | None = None
    phone: str | None = None
    source: str | None = None
    status: LeadStatus = LeadStatus.NEW
    score: float | None = None
    tags: tuple[str,...] = ()
    metadata: dict[str,Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.name.strip(): raise ValueError("lead name cannot be empty")
        if self.score is not None and not 0 <= self.score <= 1: raise ValueError("lead score must be between 0 and 1")

@dataclass(frozen=True, slots=True)
class Customer:
    name: str
    id: UUID = field(default_factory=uuid4)
    email: str | None = None
    phone: str | None = None
    status: CustomerStatus = CustomerStatus.PROSPECT
    source_lead_id: UUID | None = None
    metadata: dict[str,Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.name.strip(): raise ValueError("customer name cannot be empty")

@dataclass(frozen=True, slots=True)
class Offer:
    name: str
    price: float
    currency: str = "EUR"
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    active: bool = True
    metadata: dict[str,Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.name.strip(): raise ValueError("offer name cannot be empty")
        if self.price < 0: raise ValueError("offer price cannot be negative")
        if len(self.currency) != 3: raise ValueError("currency must be a 3-letter code")

@dataclass(frozen=True, slots=True)
class Deal:
    customer_id: UUID
    offer_id: UUID
    amount: float
    id: UUID = field(default_factory=uuid4)
    status: DealStatus = DealStatus.OPEN
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    metadata: dict[str,Any] = field(default_factory=dict)
    def __post_init__(self):
        if self.amount < 0: raise ValueError("deal amount cannot be negative")

@dataclass(frozen=True, slots=True)
class Campaign:
    name: str
    id: UUID = field(default_factory=uuid4)
    status: CampaignStatus = CampaignStatus.DRAFT
    channel: str = ""
    objective: str = ""
    budget: float | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata: dict[str,Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.name.strip(): raise ValueError("campaign name cannot be empty")
        if self.budget is not None and self.budget < 0: raise ValueError("campaign budget cannot be negative")

@dataclass(frozen=True, slots=True)
class BusinessSnapshot:
    leads: int
    qualified_leads: int
    customers: int
    open_deals: int
    won_revenue: float
    active_campaigns: int
