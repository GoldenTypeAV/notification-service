# src/worker/main.py
import asyncio
import signal
import logging
from datetime import datetime, timezone, timedelta

import redis.asyncio as aioredis

from src.shared.settings import settings
from src.shared.database import AsyncSessionLocal, engine
from src.shared.redis import (
    init_redis,
    close_redis,
    acquire_processing_lock,
    release_processing_lock,
    invalidate_history,
)
from src.shared.kafka import create_consumer, init_kafka_producer, close_kafka_producer
from src.shared.repositories.notification_repository import NotificationRepository
from src.shared.repositories.subscriber_contact_repository import SubscriberContactRepository
from src.worker.providers import get_provider
from src.worker.providers.base import SendResult
from src.shared.models.notification import NotificationStatus, NotificationChannel
from src.worker.scheduler import retry_scheduler

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None

# Уже обработанные статусы — повторно не отправляем.
_TERMINAL = {NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.DROPPED}

_RESULT_TO_STATUS = {
    SendResult.SENT: NotificationStatus.SENT,
    SendResult.DELIVERED: NotificationStatus.DELIVERED,
    SendResult.DROPPED: NotificationStatus.DROPPED,
}


def _next_retry_delay(attempt: int) -> int:
    delays = settings.retry.delays
    return delays[min(attempt - 1, len(delays) - 1)]


async def process_message(msg) -> None:
    data = msg.value
    notification_id = data["notification_id"]
    subscriber_id = data["subscriber_id"]
    channel = NotificationChannel(data["channel"])
    content = data["content"]

    async with AsyncSessionLocal() as session:
        repo = NotificationRepository(session)
        notif = await repo.get(notification_id)
        if notif is None:
            logger.warning("Notification %s not found, skipping", notification_id)
            return

        if notif.status in _TERMINAL:
            logger.info("Notification %s already %s, skipping", notification_id, notif.status.value)
            return

        # Лок не даёт Kafka-доставке и планировщику обработать одну запись дважды.
        lock_acquired = True
        if _redis is not None:
            lock_acquired = await acquire_processing_lock(
                _redis, notification_id, settings.dedup.processing_lock_ttl_sec
            )
            if not lock_acquired:
                logger.info("Notification %s is locked elsewhere, skipping", notification_id)
                return

        try:
            await _deliver(session, repo, notif, subscriber_id, channel, content)
        finally:
            if _redis is not None and lock_acquired:
                await release_processing_lock(_redis, notification_id)
                await invalidate_history(_redis, subscriber_id)


async def _deliver(session, repo, notif, subscriber_id, channel, content) -> None:
    contact_obj = await SubscriberContactRepository(session).get_contact_by_channel(
        subscriber_id, channel.value
    )
    if not contact_obj:
        await repo.update_status(
            notif.id, NotificationStatus.DROPPED, f"No contact for channel {channel.value}"
        )
        logger.warning("Notification %s dropped: no %s contact", notif.id, channel.value)
        return

    provider = get_provider(channel)
    resp = await provider.send(contact_obj.contact, content)

    if resp.result in (SendResult.SENT, SendResult.DELIVERED):
        status = _RESULT_TO_STATUS[resp.result]
        await repo.update_status(notif.id, status, resp.detail)
        logger.info("Notification %s %s via %s", notif.id, status.value, channel.value)
        return

    if resp.result is SendResult.DROPPED:
        await repo.update_status(notif.id, NotificationStatus.DROPPED, resp.detail)
        logger.warning("Notification %s dropped: %s", notif.id, resp.detail)
        return

    # Временная ошибка — планируем повтор. Счётчик берём из БД.
    new_retry = notif.retry_count + 1
    if new_retry <= settings.retry.max_attempts:
        delay = _next_retry_delay(new_retry)
        next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        await repo.update_retry(notif.id, new_retry, next_retry_at, resp.detail)
        logger.warning(
            "Notification %s failed (attempt %s/%s), retry at %s",
            notif.id, new_retry, settings.retry.max_attempts, next_retry_at,
        )
    else:
        await repo.update_status(
            notif.id, NotificationStatus.DROPPED, f"Max retries exceeded: {resp.detail}"
        )
        logger.error("Notification %s permanently failed after %s attempts", notif.id, new_retry)


async def main() -> None:
    global _redis
    _redis = await init_redis()
    producer = await init_kafka_producer()  # для планировщика ретраев

    consumer = create_consumer(settings.worker_topic, group_id=settings.kafka.group_id)
    await consumer.start()
    logger.info("Worker started on topic=%s group=%s", settings.worker_topic, settings.kafka.group_id)

    scheduler_task = None
    if settings.retry.run_scheduler:
        scheduler_task = asyncio.create_task(retry_scheduler(producer))
        logger.info("Retry scheduler enabled")

    stop = asyncio.Event()

    def _signal_handler():
        logger.info("Stopping worker...")
        stop.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, _signal_handler)
    loop.add_signal_handler(signal.SIGINT, _signal_handler)

    try:
        async for msg in consumer:
            if stop.is_set():
                break
            try:
                await process_message(msg)
                # Коммитим оффсет только после успешной обработки -> at-least-once.
                await consumer.commit()
            except Exception:
                logger.exception("Processing failed; offset NOT committed (will retry)")
    finally:
        if scheduler_task:
            scheduler_task.cancel()
        await consumer.stop()
        await close_kafka_producer()
        await close_redis()
        await engine.dispose()
        logger.info("Worker stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(main())
