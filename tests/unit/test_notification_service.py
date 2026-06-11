import pytest
from unittest.mock import AsyncMock

from src.api.v1.services.notification_service import NotificationService
from src.shared.models.notification import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
)


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_by_idempotency_keys = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def mock_producer():
    producer = AsyncMock()
    producer.send_and_wait = AsyncMock()
    return producer


def _notif(i, channel, content, priority):
    return Notification(
        id=i,
        idempotency_key=f"base:{i}",
        subscriber_id=i,
        channel=channel,
        content=content,
        priority=priority,
        status=NotificationStatus.QUEUED,
    )


@pytest.mark.asyncio
async def test_create_mass_notifications_publishes_new(mock_repo, mock_redis, mock_producer):
    service = NotificationService(mock_repo, mock_redis, mock_producer)
    ids = [1, 2, 3]
    created = [_notif(i, NotificationChannel.EMAIL, "Test", NotificationPriority.HIGH) for i in ids]
    mock_repo.insert_ignore_conflicts = AsyncMock(return_value=created)

    result = await service.create_mass_notifications(
        NotificationChannel.EMAIL, "Test", ids, NotificationPriority.HIGH, idempotency_key="base"
    )

    assert len(result) == 3
    assert mock_producer.send_and_wait.call_count == 3
    mock_producer.send_and_wait.assert_any_call(
        "notifications.high",
        value={
            "notification_id": 1,
            "subscriber_id": 1,
            "channel": "email",
            "content": "Test",
            "priority": "high",
            "retry_count": 0,
        },
    )


@pytest.mark.asyncio
async def test_duplicates_are_not_republished(mock_repo, mock_redis, mock_producer):
    service = NotificationService(mock_repo, mock_redis, mock_producer)
    existing = [_notif(1, NotificationChannel.SMS, "Hi", NotificationPriority.NORMAL)]
    mock_repo.insert_ignore_conflicts = AsyncMock(return_value=[])  # ничего нового
    mock_repo.get_by_idempotency_keys = AsyncMock(return_value=existing)

    result = await service.create_mass_notifications(
        NotificationChannel.SMS, "Hi", [1], NotificationPriority.NORMAL, idempotency_key="base"
    )

    assert result == existing
    mock_producer.send_and_wait.assert_not_called()


@pytest.mark.asyncio
async def test_get_history_uses_cache(mock_repo, mock_redis, mock_producer):
    service = NotificationService(mock_repo, mock_redis, mock_producer)
    cached = '[{"id": 1, "subscriber_id": 1, "channel": "email", "content": "Hi", "priority": "normal", "status": "queued", "created_at": "2024-01-01T00:00:00"}]'
    mock_redis.get = AsyncMock(return_value=cached)

    history = await service.get_history(1)

    assert history[0]["id"] == 1
    mock_repo.get_by_subscriber.assert_not_called()
