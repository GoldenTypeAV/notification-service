from __future__ import annotations

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.shared.models.subscriber import Subscriber

class SubscriberRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self) -> Subscriber:
        subscriber = Subscriber()
        self.db.add(subscriber)
        await self.db.commit()
        await self.db.refresh(subscriber)
        return subscriber

    async def get(self, subscriber_id: int) -> Subscriber | None:
        result = await self.db.execute(select(Subscriber).where(Subscriber.id == subscriber_id))
        return result.scalar_one_or_none()

    async def update_active(self, subscriber_id: int, is_active: bool) -> Subscriber | None:
        await self.db.execute(
            update(Subscriber).where(Subscriber.id == subscriber_id).values(is_active=is_active)
        )
        await self.db.commit()
        return await self.get(subscriber_id)

    async def delete(self, subscriber_id: int) -> bool:
        result = await self.db.execute(delete(Subscriber).where(Subscriber.id == subscriber_id))
        await self.db.commit()
        return result.rowcount > 0

    async def list(self, skip: int = 0, limit: int = 100) -> list[Subscriber]:
        result = await self.db.execute(select(Subscriber).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_active_ids(self, ids: list[int]) -> set[int]:
        """Вернуть подмножество id, которые существуют и активны."""
        if not ids:
            return set()
        result = await self.db.execute(
            select(Subscriber.id).where(
                Subscriber.id.in_(ids), Subscriber.is_active.is_(True)
            )
        )
        return set(result.scalars().all())