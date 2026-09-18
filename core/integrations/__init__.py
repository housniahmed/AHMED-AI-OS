"""Provider-neutral external integration contracts for AHMED AI OS."""
from .calendar import CalendarProvider, UnavailableCalendarProvider
from .gmail import GmailProvider, UnavailableGmailProvider
from .telegram import TelegramProvider, UnavailableTelegramProvider
from .models import CalendarEvent, EmailMessage, TelegramMessage
from .services import CalendarService, GmailService, TelegramService

__all__ = [
    "CalendarProvider", "UnavailableCalendarProvider",
    "GmailProvider", "UnavailableGmailProvider",
    "TelegramProvider", "UnavailableTelegramProvider",
    "CalendarEvent", "EmailMessage", "TelegramMessage",
    "CalendarService", "GmailService", "TelegramService",
]
