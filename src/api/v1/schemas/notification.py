from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from src.shared.models.notification import (
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
)


class SingleNotificationRequest(BaseModel):
    channel: NotificationChannel
    content: str = Field(..., min_length=1, max_length=4096)
    subscriber_id: int
    priority: NotificationPriority = NotificationPriority.NORMAL
    idempotency_key: str | None = Field(default=None, max_length=255)


class BulkNotificationRequest(BaseModel):
    channel: NotificationChannel
    content: str = Field(..., min_length=1, max_length=4096)
    subscriber_ids: list[int] = Field(..., min_length=1)
    priority: NotificationPriority = NotificationPriority.NORMAL
    idempotency_key: str | None = Field(default=None, max_length=255)


class NotificationStatusResponse(BaseModel):
    id: int
    subscriber_id: int
    channel: NotificationChannel
    content: str
    priority: NotificationPriority
    status: NotificationStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
