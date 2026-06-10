from datetime import datetime
from enum import Enum
from sqlalchemy import String, Text, DateTime, func, Enum as SQLEnum, BigInteger, Index
from sqlalchemy.orm import Mapped, mapped_column
from shared.models.base import Base

class NotificationChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"

class NotificationPriority(str, Enum):
    HIGH = "high"       # высокий приоритет
    NORMAL = "normal"   # низкий приоритет

class NotificationStatus(str, Enum):
    QUEUED = "queued"           # в очереди
    SENT = "sent"               # отправлено провайдеру
    DELIVERED = "delivered"     # доставлено (подтверждение)
    DROPPED = "dropped"         # отброшено (ошибка)

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    subscriber_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(SQLEnum(NotificationChannel), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[NotificationPriority] = mapped_column(
        SQLEnum(NotificationPriority), 
        default=NotificationPriority.NORMAL,
        nullable=False,
        index=True
    )
    status: Mapped[NotificationStatus] = mapped_column(
        SQLEnum(NotificationStatus),
        default=NotificationStatus.QUEUED,
        nullable=False,
        index=True
    )
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_notifications_subscriber_status", "subscriber_id", "status"),
    )