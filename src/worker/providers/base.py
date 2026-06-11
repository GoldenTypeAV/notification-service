from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class SendResult(str, Enum):
    """Результат попытки отправки через провайдера/шлюз."""
    SENT = "sent"            # принято шлюзом, доставка ещё не подтверждена
    DELIVERED = "delivered"  # шлюз подтвердил доставку
    DROPPED = "dropped"      # постоянная ошибка (несуществующий адрес и т.п.) — ретрай не нужен
    FAILED = "failed"        # временная ошибка — нужен повтор


@dataclass(slots=True)
class ProviderResponse:
    result: SendResult
    detail: str = ""

    @property
    def is_retryable(self) -> bool:
        return self.result is SendResult.FAILED


class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, to: str, content: str) -> ProviderResponse:
        """Отправить сообщение и вернуть ProviderResponse."""
        ...
