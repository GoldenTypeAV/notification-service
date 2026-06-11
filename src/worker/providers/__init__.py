from typing import Callable

from .base import NotificationProvider
from .email_provider import MockEmailProvider, SMTPEmailProvider
from .sms_provider import MockSMSProvider
from src.shared.models.notification import NotificationChannel
from src.shared.settings import settings


def _email_provider() -> NotificationProvider:
    name = settings.email.provider
    if name == "mock":
        return MockEmailProvider()
    if name == "smtp":
        return SMTPEmailProvider()
    raise ValueError(f"Unknown email provider: {name}")


def _sms_provider() -> NotificationProvider:
    name = settings.sms.provider
    if name == "mock":
        return MockSMSProvider()
    raise ValueError(f"Unknown sms provider: {name}")


_FACTORIES: dict[NotificationChannel, Callable[[], NotificationProvider]] = {
    NotificationChannel.EMAIL: _email_provider,
    NotificationChannel.SMS: _sms_provider,
}

_PROVIDER_NAME = {
    NotificationChannel.EMAIL: lambda: settings.email.provider,
    NotificationChannel.SMS: lambda: settings.sms.provider,
}

_cache: dict[tuple, NotificationProvider] = {}


def get_provider(channel: NotificationChannel) -> NotificationProvider:
    factory = _FACTORIES.get(channel)
    if factory is None:
        raise ValueError(f"No provider registered for channel {channel}")
    key = (channel, _PROVIDER_NAME[channel]())
    if key not in _cache:
        _cache[key] = factory()
    return _cache[key]
