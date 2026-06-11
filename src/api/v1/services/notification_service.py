import json
import logging
import uuid
from datetime import datetime, timezone, timedelta

from redis.asyncio import Redis
from aiokafka import AIOKafkaProducer

from src.shared.repositories.notification_repository import NotificationRepository
from src.shared.models.notification import (
    Notification,
    NotificationPriority,
    NotificationChannel,
    NotificationStatus,
)
from src.shared.redis import (
    history_cache_key,
    invalidate_history,
    claim_idempotency,
)
from src.shared.settings import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, repo: NotificationRepository, redis: Redis, kafka_producer: AIOKafkaProducer):
        self.repo = repo
        self.redis = redis
        self.producer = kafka_producer

    async def create_mass_notifications(
        self,
        channel: NotificationChannel,
        content: str,
        subscriber_ids: list[int],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        idempotency_key: str | None = None,
    ) -> list[Notification]:
        """Создать уведомления и опубликовать их в Kafka.

        Ключ идемпотентности — `{idempotency_key}:{subscriber_id}`. Повтор с тем же
        ключом не создаёт дублей и не публикует сообщения заново.
        """
        base_key = idempotency_key or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        stuck_deadline = now + timedelta(seconds=settings.retry.stuck_after_sec)

        unique_ids = list(dict.fromkeys(subscriber_ids))
        keys = {sub_id: f"{base_key}:{sub_id}" for sub_id in unique_ids}

        rows = [
            {
                "idempotency_key": keys[sub_id],
                "subscriber_id": sub_id,
                "channel": channel,
                "content": content,
                "priority": priority,
                "status": NotificationStatus.QUEUED,
                "next_retry_at": stuck_deadline,
            }
            for sub_id in unique_ids
        ]

        inserted = await self.repo.insert_ignore_conflicts(rows)
        inserted_keys = {n.idempotency_key for n in inserted}

        dup_keys = [k for k in keys.values() if k not in inserted_keys]
        existing = await self.repo.get_by_idempotency_keys(dup_keys)

        for notif in inserted:
            await self._publish(notif)

        for notif in inserted:
            await self._mark_idempotent(notif.idempotency_key)
        for sub_id in {n.subscriber_id for n in inserted}:
            await self._safe_invalidate(sub_id)

        return inserted + existing

    async def _mark_idempotent(self, key: str) -> None:
        try:
            await claim_idempotency(self.redis, key, settings.dedup.idempotency_ttl_sec)
        except Exception:  # noqa: BLE001
            pass

    async def _safe_invalidate(self, subscriber_id: int) -> None:
        try:
            await invalidate_history(self.redis, subscriber_id)
        except Exception:  # noqa: BLE001
            pass

    async def _publish(self, notif: Notification) -> None:
        topic = settings.topic_for_priority(notif.priority.value)
        payload = {
            "notification_id": notif.id,
            "subscriber_id": notif.subscriber_id,
            "channel": notif.channel.value,
            "content": notif.content,
            "priority": notif.priority.value,
            "retry_count": 0,
        }
        try:
            await self.producer.send_and_wait(topic, value=payload)
        except Exception as e:  # noqa: BLE001
            # Запись уже в БД как QUEUED — её переотправит планировщик.
            logger.warning("Kafka publish failed for notification %s: %s", notif.id, e)

    async def get_history(self, subscriber_id: int) -> list[dict]:
        """История уведомлений подписчика с краткосрочным кэшем в Redis."""
        cache_key = history_cache_key(subscriber_id)
        try:
            cached = await self.redis.get(cache_key)
        except Exception:  # noqa: BLE001
            cached = None
        if cached:
            return json.loads(cached)

        notifications = await self.repo.get_by_subscriber(subscriber_id)
        data = [
            {
                "id": n.id,
                "subscriber_id": n.subscriber_id,
                "channel": n.channel.value,
                "content": n.content,
                "priority": n.priority.value,
                "status": n.status.value,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ]
        try:
            await self.redis.setex(
                cache_key, settings.dedup.history_cache_ttl_sec, json.dumps(data)
            )
        except Exception:  # noqa: BLE001
            pass
        return data
