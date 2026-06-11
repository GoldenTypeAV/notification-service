from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.services.notification_service import NotificationService
from src.shared.repositories.notification_repository import NotificationRepository
from src.shared.repositories.subscriber_repository import SubscriberRepository
from src.api.v1.schemas.notification import (
    SingleNotificationRequest,
    BulkNotificationRequest,
    NotificationStatusResponse,
)
from src.shared.database import get_db
from src.shared.redis import get_redis
from src.shared.kafka import get_producer as get_kafka_producer

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def get_notification_service(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    producer=Depends(get_kafka_producer),
) -> NotificationService:
    repo = NotificationRepository(db)
    return NotificationService(repo, redis, producer)


# Один и тот же AsyncSession переиспользуется для проверки получателей.
async def get_subscriber_repo(db: AsyncSession = Depends(get_db)) -> SubscriberRepository:
    return SubscriberRepository(db)


@router.post("/single", status_code=status.HTTP_202_ACCEPTED)
async def single_notification(
    request: SingleNotificationRequest,
    service: NotificationService = Depends(get_notification_service),
    subscriber_repo: SubscriberRepository = Depends(get_subscriber_repo),
):
    """Отправка уведомления одному подписчику. Возвращает 202 Accepted."""
    active = await subscriber_repo.get_active_ids([request.subscriber_id])
    if not active:
        raise HTTPException(status_code=404, detail="Subscriber not found or inactive")

    notifications = await service.create_mass_notifications(
        channel=request.channel,
        content=request.content,
        subscriber_ids=[request.subscriber_id],
        priority=request.priority,
        idempotency_key=request.idempotency_key,
    )
    return {"status": "accepted", "count": len(notifications)}


@router.post("/bulk", status_code=status.HTTP_202_ACCEPTED)
async def mass_notifications(
    request: BulkNotificationRequest,
    service: NotificationService = Depends(get_notification_service),
    subscriber_repo: SubscriberRepository = Depends(get_subscriber_repo),
):
    """Массовая рассылка. Неактивные/несуществующие получатели отбрасываются.
    Возвращает 202 Accepted и счётчики."""
    active = await subscriber_repo.get_active_ids(request.subscriber_ids)
    if not active:
        raise HTTPException(status_code=400, detail="No valid (active) recipients")

    # Сохраняем исходный порядок, отфильтровав по активным.
    target_ids = [sid for sid in request.subscriber_ids if sid in active]
    notifications = await service.create_mass_notifications(
        channel=request.channel,
        content=request.content,
        subscriber_ids=target_ids,
        priority=request.priority,
        idempotency_key=request.idempotency_key,
    )
    return {
        "status": "accepted",
        "requested": len(request.subscriber_ids),
        "accepted": len(notifications),
    }


@router.get("/history/{subscriber_id}", response_model=list[NotificationStatusResponse])
async def get_notification_history(
    subscriber_id: int,
    service: NotificationService = Depends(get_notification_service),
):
    """История и текущие статусы уведомлений конкретного подписчика."""
    return await service.get_history(subscriber_id)
