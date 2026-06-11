from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.shared.database import get_db
from src.shared.models.notification import Notification, NotificationStatus
from src.shared.kafka import get_producer
from src.shared.settings import settings

router = APIRouter(prefix="/admin/notifications", tags=["admin"])


@router.post("/retry")
async def mass_retry_dropped(
    subscriber_id: int | None = Query(None),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    producer=Depends(get_producer),
):
    """Перезапустить отброшенные (DROPPED) уведомления. Опционально по subscriber_id."""
    query = select(Notification).where(Notification.status == NotificationStatus.DROPPED)
    if subscriber_id is not None:
        query = query.where(Notification.subscriber_id == subscriber_id)
    query = query.limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()
    if not notifications:
        return {"message": "No dropped notifications found", "retried": 0}

    now = datetime.now(timezone.utc)
    for n in notifications:
        n.status = NotificationStatus.QUEUED
        n.retry_count = 0
        n.next_retry_at = now
        n.provider_response = None
    await db.commit()

    for n in notifications:
        topic = settings.topic_for_priority(n.priority.value)
        await producer.send_and_wait(
            topic,
            value={
                "notification_id": n.id,
                "subscriber_id": n.subscriber_id,
                "channel": n.channel.value,
                "content": n.content,
                "priority": n.priority.value,
                "retry_count": 0,
            },
        )

    return {"retried": len(notifications)}
