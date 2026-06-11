import uuid
from types import SimpleNamespace

import pytest

from src.worker.main import process_message
from src.shared.settings import settings
from src.shared.repositories.notification_repository import NotificationRepository
from src.shared.repositories.subscriber_repository import SubscriberRepository
from src.shared.repositories.subscriber_contact_repository import SubscriberContactRepository
from src.shared.models.notification import (
    NotificationStatus,
    NotificationChannel,
    NotificationPriority,
)


def _message(notification_id, subscriber_id):
    return SimpleNamespace(
        value={
            "notification_id": notification_id,
            "subscriber_id": subscriber_id,
            "channel": "email",
            "content": "Test",
            "priority": "high",
            "retry_count": 0,
        }
    )


async def _seed(session_factory, with_contact: bool):
    async with session_factory() as s:
        sub = await SubscriberRepository(s).create()
        if with_contact:
            await SubscriberContactRepository(s).add_contact(
                sub.id, NotificationChannel.EMAIL.value, "user@example.com", True
            )
        notif = await NotificationRepository(s).create(
            idempotency_key=str(uuid.uuid4()),
            subscriber_id=sub.id,
            channel=NotificationChannel.EMAIL,
            content="Test",
            priority=NotificationPriority.HIGH,
            status=NotificationStatus.QUEUED,
        )
        return sub.id, notif.id


async def _status(session_factory, notification_id):
    async with session_factory() as s:
        notif = await NotificationRepository(s).get(notification_id)
        return notif.status


@pytest.mark.asyncio
async def test_worker_delivers_via_mock_provider(session_factory, monkeypatch):
    monkeypatch.setattr(settings.email, "provider", "mock")
    sub_id, notif_id = await _seed(session_factory, with_contact=True)

    await process_message(_message(notif_id, sub_id))

    assert await _status(session_factory, notif_id) is NotificationStatus.DELIVERED


@pytest.mark.asyncio
async def test_worker_drops_when_no_contact(session_factory, monkeypatch):
    monkeypatch.setattr(settings.email, "provider", "mock")
    sub_id, notif_id = await _seed(session_factory, with_contact=False)

    await process_message(_message(notif_id, sub_id))

    assert await _status(session_factory, notif_id) is NotificationStatus.DROPPED
