"""In-memory business repository contract for deterministic core workflows."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID
from .models import Lead, Customer, Offer, Deal, Campaign
T=TypeVar("T")
class BusinessRepository(ABC):
    @abstractmethod
    def save(self, entity:T)->T: raise NotImplementedError
    @abstractmethod
    def get(self, entity_id:UUID)->T: raise NotImplementedError
    @abstractmethod
    def list(self, entity_type:type[T])->tuple[T,...]: raise NotImplementedError
class InMemoryBusinessRepository(BusinessRepository):
    def __init__(self): self._data={}
    def save(self,entity): self._data[entity.id]=entity; return entity
    def get(self,entity_id):
        try: return self._data[entity_id]
        except KeyError as exc: raise KeyError(f"unknown business entity: {entity_id}") from exc
    def list(self,entity_type): return tuple(x for x in self._data.values() if isinstance(x,entity_type))
