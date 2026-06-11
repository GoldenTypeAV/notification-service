import logging

from .base import NotificationProvider, ProviderResponse, SendResult

logger = logging.getLogger(__name__)


class MockSMSProvider(NotificationProvider):
    async def send(self, to: str, content: str) -> ProviderResponse:
        logger.info("[MOCK SMS] to=%s content=%s", to, content)
        return ProviderResponse(SendResult.DELIVERED, "mocked")
