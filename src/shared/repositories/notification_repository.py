# src/shared/repositories/notification_repository.py
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.notification import Notification, NotificationStatus


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Notification:
        """Создать и сохранить одно уведомление в БД."""
        notification = Notification(**kwargs)
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def insert_ignore_conflicts(self, rows: list[dict]) -> list[Notification]:
        """Bulk-вставка с ON CONFLICT DO NOTHING по idempotency_key.

        Возвращает только реально созданные записи (дубли пропускаются БД).
        """
        if not rows:
            return []
        stmt = (
            pg_insert(Notification)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(Notification)
        )
        result = await self.db.execute(
            stmt, execution_options={"populate_existing": True}
        )
        await self.db.commit()
        return list(result.scalars().all())

    async def get(self, notification_id: int) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_by_subscriber(self, subscriber_id: int) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.subscriber_id == subscriber_id)
            .order_by(Notification.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_idempotency_key(self, key: str) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(Notification.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_keys(self, keys: list[str]) -> list[Notification]:
        if not keys:
            return []
        result = await self.db.execute(
            select(Notification).where(Notification.idempotency_key.in_(keys))
        )
        return list(result.scalars().all())

    async def exists_by_idempotency_key(self, key: str) -> bool:
        result = await self.db.execute(
            select(Notification.id).where(Notification.idempotency_key == key).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def update_status(
        self,
        notification_id: int,
        status: NotificationStatus,
        provider_response: str | None = None,
    ) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(
                status=status,
                provider_response=provider_response,
                next_retry_at=None,
            )
        )
        await self.db.commit()

    async def update_retry(
        self,
        notification_id: int,
        retry_count: int,
        next_retry_at: datetime,
        provider_response: str | None = None,
    ) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(
                status=NotificationStatus.QUEUED,
                retry_count=retry_count,
                next_retry_at=next_retry_at,
                provider_response=provider_response,
            )
        )
        await self.db.commit()
