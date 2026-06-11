from datetime import datetime
from enum import Enum
import functools
from sqlalchemy import String, Text, DateTime, func, Enum as SQLEnum, BigInteger, Index
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


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


# Хранить в БД значения енама (lowercase), а не имена.
PgEnum = functools.partial(SQLEnum, values_callable=lambda e: [m.value for m in e])

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    subscriber_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(PgEnum(NotificationChannel), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[NotificationPriority] = mapped_column(
        PgEnum(NotificationPriority),
        default=NotificationPriority.NORMAL,
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        PgEnum(NotificationStatus),
        default=NotificationStatus.QUEUED,
        nullable=False,
    )
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_notifications_status_retry", "status", "next_retry_at"),
        Index("ix_notifications_subscriber_created", "subscriber_id", "created_at"),
    )