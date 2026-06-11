import logging

import aiosmtplib
from email.message import EmailMessage

from src.shared.settings import settings
from .base import NotificationProvider, ProviderResponse, SendResult

logger = logging.getLogger(__name__)


class SMTPEmailProvider(NotificationProvider):
    def __init__(self):
        self.host = settings.email.host
        self.port = settings.email.port
        self.from_email = settings.email.from_email

    async def send(self, to: str, content: str) -> ProviderResponse:
        msg = EmailMessage()
        msg["From"] = self.from_email
        msg["To"] = to
        msg["Subject"] = "Notification"
        msg.set_content(content)

        try:
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                use_tls=settings.email.use_tls,
            )
            return ProviderResponse(SendResult.SENT, "accepted by smtp")
        except aiosmtplib.SMTPRecipientsRefused as e:
            return ProviderResponse(SendResult.DROPPED, f"recipient refused: {e}")
        except aiosmtplib.SMTPException as e:
            return ProviderResponse(SendResult.FAILED, f"smtp error: {e}")
        except Exception as e:  # noqa: BLE001
            return ProviderResponse(SendResult.FAILED, f"unexpected: {e}")


class MockEmailProvider(NotificationProvider):
    async def send(self, to: str, content: str) -> ProviderResponse:
        logger.info("[MOCK EMAIL] to=%s content=%s", to, content)
        return ProviderResponse(SendResult.DELIVERED, "mocked")
