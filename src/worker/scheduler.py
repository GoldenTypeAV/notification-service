import asyncio
import logging
from datetime import datetime, timezone, timedelta

from aiokafka import AIOKafkaProducer
from sqlalchemy import select

from src.shared.database import AsyncSessionLocal
from src.shared.models.notification import Notification, NotificationStatus
from src.shared.settings import settings

logger = logging.getLogger(__name__)


async def _run_once(producer: AIOKafkaProducer) -> int:
    now = datetime.now(timezone.utc)
    # Сдвигаем next_retry_at вперёд, чтобы запись переотправилась снова,
    # если так и не будет обработана.
    rearm = now + timedelta(seconds=settings.retry.stuck_after_sec)

    async with AsyncSessionLocal() as session:
        # SKIP LOCKED: несколько воркеров не возьмут одни и те же строки.
        result = await session.execute(
            select(Notification)
            .where(Notification.status == NotificationStatus.QUEUED)
            .where(Notification.next_retry_at.is_not(None))
            .where(Notification.next_retry_at <= now)
            .order_by(Notification.priority.desc(), Notification.next_retry_at)
            .limit(settings.retry.scheduler_batch_size)
            .with_for_update(skip_locked=True)
        )
        notifications = result.scalars().all()
        if not notifications:
            return 0

        for notif in notifications:
            topic = settings.topic_for_priority(notif.priority.value)
            await producer.send_and_wait(
                topic,
                value={
                    "notification_id": notif.id,
                    "subscriber_id": notif.subscriber_id,
                    "channel": notif.channel.value,
                    "content": notif.content,
                    "priority": notif.priority.value,
                    "retry_count": notif.retry_count,
                },
            )
            notif.next_retry_at = rearm

        await session.commit()
        return len(notifications)


async def retry_scheduler(producer: AIOKafkaProducer) -> None:
    """Периодически переотправляет в Kafka уведомления, готовые к повтору."""
    while True:
        try:
            count = await _run_once(producer)
            if count:
                logger.info("Retry scheduler re-published %s notification(s)", count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Retry scheduler iteration failed")
        await asyncio.sleep(settings.retry.scheduler_interval_sec)
