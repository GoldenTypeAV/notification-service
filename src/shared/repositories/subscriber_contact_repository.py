from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.shared.models.subscriber import SubscriberContact

class SubscriberContactRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_contact(
        self, subscriber_id: int, channel: str, contact: str, is_verified: bool = False
    ) -> SubscriberContact:
        contact_obj = SubscriberContact(
            subscriber_id=subscriber_id,
            channel=channel,
            contact=contact,
            is_verified=is_verified,
        )
        self.db.add(contact_obj)
        await self.db.commit()
        await self.db.refresh(contact_obj)
        return contact_obj

    async def get_contacts(self, subscriber_id: int) -> list[SubscriberContact]:
        result = await self.db.execute(
            select(SubscriberContact).where(SubscriberContact.subscriber_id == subscriber_id)
        )
        return list(result.scalars().all())

    async def get_contact_by_channel(self, subscriber_id: int, channel: str) -> SubscriberContact | None:
        result = await self.db.execute(
            select(SubscriberContact)
            .where(SubscriberContact.subscriber_id == subscriber_id)
            .where(SubscriberContact.channel == channel)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_contact(self, contact_id: int, **kwargs) -> SubscriberContact | None:
        await self.db.execute(update(SubscriberContact).where(SubscriberContact.id == contact_id).values(**kwargs))
        await self.db.commit()
        result = await self.db.execute(select(SubscriberContact).where(SubscriberContact.id == contact_id))
        return result.scalar_one_or_none()

    async def delete_contact(self, contact_id: int) -> bool:
        result = await self.db.execute(delete(SubscriberContact).where(SubscriberContact.id == contact_id))
        await self.db.commit()
        return result.rowcount > 0