import aiosmtplib
from email.message import EmailMessage
from src.shared.settings import settings
from .base import NotificationProvider

class SMTPEmailProvider(NotificationProvider):
    def __init__(self):
        self.host = settings.email.host
        self.port = settings.email.port
        self.from_email = settings.email.from_email

    async def send(self, to: str, content: str) -> tuple[bool, str]:
        try:
            msg = EmailMessage()
            msg["From"] = self.from_email
            msg["To"] = to
            msg["Subject"] = "Notification"
            msg.set_content(content)

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                use_tls=settings.email.use_tls,
            )
            return True, "sent"
        except Exception as e:
            return False, str(e)

class MockEmailProvider(NotificationProvider):
    async def send(self, to: str, content: str) -> tuple[bool, str]:
        print(f"[MOCK EMAIL] To={to}, Content={content}")
        return True, "mocked"