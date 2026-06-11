import pytest

from src.worker.providers import get_provider
from src.worker.providers.base import SendResult
from src.worker.providers.email_provider import MockEmailProvider, SMTPEmailProvider
from src.worker.providers.sms_provider import MockSMSProvider
from src.shared.models.notification import NotificationChannel
from src.shared.settings import settings


def test_get_email_provider_mock(monkeypatch):
    monkeypatch.setattr(settings.email, "provider", "mock")
    assert isinstance(get_provider(NotificationChannel.EMAIL), MockEmailProvider)


def test_get_email_provider_smtp(monkeypatch):
    monkeypatch.setattr(settings.email, "provider", "smtp")
    assert isinstance(get_provider(NotificationChannel.EMAIL), SMTPEmailProvider)


def test_get_sms_provider(monkeypatch):
    monkeypatch.setattr(settings.sms, "provider", "mock")
    assert isinstance(get_provider(NotificationChannel.SMS), MockSMSProvider)


def test_unknown_channel():
    with pytest.raises(ValueError):
        get_provider("unknown")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_mock_provider_returns_delivered(monkeypatch):
    monkeypatch.setattr(settings.sms, "provider", "mock")
    resp = await get_provider(NotificationChannel.SMS).send("+1234567", "hi")
    assert resp.result is SendResult.DELIVERED
