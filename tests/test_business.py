import pytest
from core.business.models import *
from core.business.repository import InMemoryBusinessRepository
from core.business.services import BusinessOS

def test_lead_score_is_bounded():
    with pytest.raises(ValueError): Lead("A", score=1.2)

def test_offer_price_is_non_negative():
    with pytest.raises(ValueError): Offer("x", -1)

def test_business_snapshot():
    repo=InMemoryBusinessRepository(); os=BusinessOS(repo)
    lead=os.add_lead(Lead("Alice",score=.9)); os.qualify_lead(lead.id)
    customer=os.add_customer(Customer("Alice",source_lead_id=lead.id))
    offer=os.add_offer(Offer("Service",100))
    os.open_deal(Deal(customer.id,offer.id,100,status=DealStatus.WON))
    os.add_campaign(Campaign("Launch",status=CampaignStatus.ACTIVE))
    s=os.snapshot()
    assert s.leads==1 and s.qualified_leads==1 and s.customers==1 and s.won_revenue==100 and s.active_campaigns==1

def test_empty_names_rejected():
    with pytest.raises(ValueError): Lead(" ")
    with pytest.raises(ValueError): Customer(" ")
    with pytest.raises(ValueError): Campaign(" ")
