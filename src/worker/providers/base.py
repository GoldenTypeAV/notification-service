from abc import ABC, abstractmethod

class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, to: str, content: str) -> tuple[bool, str]:
        """Return (success, response)"""
        pass