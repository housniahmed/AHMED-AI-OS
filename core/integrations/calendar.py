"""Calendar integration port and an explicit unavailable implementation."""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from .models import CalendarEvent

class CalendarProvider(ABC):
    @abstractmethod
    def list_events(self, start_at: datetime, end_at: datetime) -> tuple[CalendarEvent, ...]: raise NotImplementedError
    @abstractmethod
    def create_event(self, event: CalendarEvent) -> CalendarEvent: raise NotImplementedError
    @abstractmethod
    def update_event(self, event: CalendarEvent) -> CalendarEvent: raise NotImplementedError
    @abstractmethod
    def delete_event(self, external_id: str) -> None: raise NotImplementedError

class UnavailableCalendarProvider(CalendarProvider):
    def _raise(self) -> None: raise RuntimeError("calendar provider is not configured")
    def list_events(self, start_at: datetime, end_at: datetime): self._raise()
    def create_event(self, event: CalendarEvent): self._raise()
    def update_event(self, event: CalendarEvent): self._raise()
    def delete_event(self, external_id: str) -> None: self._raise()
