"""Telegram integration port and an explicit unavailable implementation."""
from __future__ import annotations
from abc import ABC, abstractmethod
from .models import TelegramMessage

class TelegramProvider(ABC):
    @abstractmethod
    def send_message(self, message: TelegramMessage) -> TelegramMessage: raise NotImplementedError

class UnavailableTelegramProvider(TelegramProvider):
    def send_message(self, message: TelegramMessage):
        raise RuntimeError("Telegram provider is not configured")
