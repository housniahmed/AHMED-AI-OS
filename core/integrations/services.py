"""Application services for B26 integrations.

These services remain provider-neutral and intentionally do not perform authorization.
Authorization and execution policy stay in the existing tool/gateway layers.
"""
from __future__ import annotations
from datetime import datetime
from .calendar import CalendarProvider
from .gmail import GmailProvider
from .telegram import TelegramProvider
from .models import CalendarEvent, EmailMessage, TelegramMessage

class CalendarService:
    def __init__(self, provider: CalendarProvider) -> None: self.provider = provider
    def list_events(self, start_at: datetime, end_at: datetime): return self.provider.list_events(start_at, end_at)
    def create_event(self, event: CalendarEvent): return self.provider.create_event(event)
    def update_event(self, event: CalendarEvent): return self.provider.update_event(event)
    def delete_event(self, external_id: str) -> None: self.provider.delete_event(external_id)

class GmailService:
    def __init__(self, provider: GmailProvider) -> None: self.provider = provider
    def search(self, query: str, limit: int = 20):
        if not query.strip(): raise ValueError("gmail query cannot be empty")
        if limit < 1 or limit > 100: raise ValueError("gmail limit must be between 1 and 100")
        return self.provider.search(query, limit)
    def get(self, external_id: str): return self.provider.get(external_id)
    def create_draft(self, message: EmailMessage): return self.provider.create_draft(message)
    def send(self, message: EmailMessage): return self.provider.send(message)

class TelegramService:
    def __init__(self, provider: TelegramProvider) -> None: self.provider = provider
    def send_message(self, message: TelegramMessage): return self.provider.send_message(message)
