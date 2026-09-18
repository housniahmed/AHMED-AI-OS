from datetime import datetime, timezone, timedelta
import pytest
from core.integrations.models import CalendarEvent, EmailMessage, TelegramMessage
from core.integrations.calendar import UnavailableCalendarProvider
from core.integrations.gmail import UnavailableGmailProvider
from core.integrations.telegram import UnavailableTelegramProvider

def test_calendar_event_validates_interval():
    start=datetime(2026,1,1,10,tzinfo=timezone.utc)
    with pytest.raises(ValueError): CalendarEvent("x", start, start)

def test_email_requires_recipient():
    with pytest.raises(ValueError): EmailMessage("s", "a@example.com", ())

def test_telegram_requires_text():
    with pytest.raises(ValueError): TelegramMessage("123", "")

def test_unavailable_providers_fail_explicitly():
    start=datetime(2026,1,1,10,tzinfo=timezone.utc)
    end=start+timedelta(hours=1)
    with pytest.raises(RuntimeError): UnavailableCalendarProvider().list_events(start,end)
    with pytest.raises(RuntimeError): UnavailableGmailProvider().search("from:test")
    with pytest.raises(RuntimeError): UnavailableTelegramProvider().send_message(TelegramMessage("123","hello"))
