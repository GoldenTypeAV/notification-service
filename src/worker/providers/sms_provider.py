from .base import NotificationProvider
from src.shared.settings import settings

class MockSMSProvider(NotificationProvider):
    async def send(self, to: str, content: str) -> tuple[bool, str]:
        print(f"[MOCK SMS] To={to}, Content={content}")
        return True, "mocked"