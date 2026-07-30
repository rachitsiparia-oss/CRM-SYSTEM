import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

NotificationPriority = Literal["low", "normal", "high", "urgent"]


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipient_staff_id: uuid.UUID
    notification_type: str
    title: str
    body: str | None
    priority: str
    record_type: str | None
    record_id: uuid.UUID | None
    read_at: datetime | None
    dismissed_at: datetime | None
    actioned_at: datetime | None
    created_at: datetime


class NotificationBroadcastIn(BaseModel):
    recipient_staff_ids: list[uuid.UUID]
    title: str
    body: str | None = None
    priority: NotificationPriority = "normal"
