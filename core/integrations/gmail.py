"""Gmail integration port and an explicit unavailable implementation."""
from __future__ import annotations
from abc import ABC, abstractmethod
from .models import EmailMessage

class GmailProvider(ABC):
    @abstractmethod
    def search(self, query: str, limit: int = 20) -> tuple[EmailMessage, ...]: raise NotImplementedError
    @abstractmethod
    def get(self, external_id: str) -> EmailMessage: raise NotImplementedError
    @abstractmethod
    def create_draft(self, message: EmailMessage) -> EmailMessage: raise NotImplementedError
    @abstractmethod
    def send(self, message: EmailMessage) -> EmailMessage: raise NotImplementedError

class UnavailableGmailProvider(GmailProvider):
    def _raise(self) -> None: raise RuntimeError("Gmail provider is not configured")
    def search(self, query: str, limit: int = 20): self._raise()
    def get(self, external_id: str): self._raise()
    def create_draft(self, message: EmailMessage): self._raise()
    def send(self, message: EmailMessage): self._raise()
