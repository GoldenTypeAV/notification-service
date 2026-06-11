import re

from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime
from src.shared.models.notification import NotificationChannel

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


class SubscriberResponse(BaseModel):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriberContactCreate(BaseModel):
    channel: NotificationChannel
    contact: str = Field(..., min_length=1, max_length=255)
    is_verified: bool = False

    @model_validator(mode="after")
    def validate_contact_format(self):
        if self.channel is NotificationChannel.EMAIL and not _EMAIL_RE.match(self.contact):
            raise ValueError("Invalid email address")
        if self.channel is NotificationChannel.SMS and not _PHONE_RE.match(self.contact):
            raise ValueError("Invalid phone number")
        return self


class SubscriberContactResponse(BaseModel):
    id: int
    subscriber_id: int
    channel: str
    contact: str
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriberUpdateActive(BaseModel):
    is_active: bool
