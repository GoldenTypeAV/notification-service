from sqlalchemy.ext.asyncio import AsyncSession
from src.shared.repositories.subscriber_repository import SubscriberRepository
from src.shared.repositories.subscriber_contact_repository import SubscriberContactRepository
from src.shared.models.subscriber import Subscriber

class SubscriberService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.subscriber_repo = SubscriberRepository(db)
        self.contact_repo = SubscriberContactRepository(db)

    # ----- Subscriber CRUD -----
    async def create_subscriber(self) -> Subscriber:
        return await self.subscriber_repo.create()

    async def get_subscriber(self, subscriber_id: int) -> Subscriber | None:
        return await self.subscriber_repo.get(subscriber_id)

    async def update_active(self, subscriber_id: int, is_active: bool) -> Subscriber | None:
        return await self.subscriber_repo.update_active(subscriber_id, is_active)

    async def delete_subscriber(self, subscriber_id: int) -> bool:
        # каскад удалит контакты автоматически (ondelete=CASCADE)
        return await self.subscriber_repo.delete(subscriber_id)

    async def list_subscribers(self, skip: int = 0, limit: int = 100) -> list[Subscriber]:
        return await self.subscriber_repo.list(skip, limit)

    # ----- Contacts management -----
    async def add_contact(self, subscriber_id: int, channel: str, contact: str, is_verified: bool = False):
        subscriber = await self.subscriber_repo.get(subscriber_id)
        if not subscriber:
            return None
        return await self.contact_repo.add_contact(subscriber_id, channel, contact, is_verified)

    async def get_contacts(self, subscriber_id: int):
        return await self.contact_repo.get_contacts(subscriber_id)

    async def update_contact(self, contact_id: int, **kwargs):
        return await self.contact_repo.update_contact(contact_id, **kwargs)

    async def delete_contact(self, contact_id: int):
        return await self.contact_repo.delete_contact(contact_id)