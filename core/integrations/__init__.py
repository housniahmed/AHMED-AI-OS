"""Provider-neutral external integration contracts for AHMED AI OS."""
from .calendar import CalendarProvider
from .gmail import GmailProvider
from .telegram import TelegramProvider
from .models import CalendarEvent, EmailMessage, TelegramMessage

__all__ = ["CalendarProvider", "GmailProvider", "TelegramProvider", "CalendarEvent", "EmailMessage", "TelegramMessage"]
