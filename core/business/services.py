"""Deterministic Business OS application services; no CRM/ads/payment SDKs here."""
from __future__ import annotations
from .models import *
from .repository import BusinessRepository
class BusinessOS:
    def __init__(self, repository:BusinessRepository): self.repo=repository
    def add_lead(self,lead:Lead): return self.repo.save(lead)
    def qualify_lead(self,lead_id):
        lead=self.repo.get(lead_id); return self.repo.save(Lead(lead.name,lead.id,lead.email,lead.phone,lead.source,LeadStatus.QUALIFIED,lead.score,lead.tags,lead.metadata))
    def add_customer(self,customer:Customer): return self.repo.save(customer)
    def add_offer(self,offer:Offer): return self.repo.save(offer)
    def open_deal(self,deal:Deal): return self.repo.save(deal)
    def add_campaign(self,campaign:Campaign): return self.repo.save(campaign)
    def snapshot(self)->BusinessSnapshot:
        leads=self.repo.list(Lead); customers=self.repo.list(Customer); deals=self.repo.list(Deal); campaigns=self.repo.list(Campaign)
        return BusinessSnapshot(len(leads),sum(x.status is LeadStatus.QUALIFIED for x in leads),len(customers),sum(x.status is DealStatus.OPEN for x in deals),sum(x.amount for x in deals if x.status is DealStatus.WON),sum(x.status is CampaignStatus.ACTIVE for x in campaigns))
