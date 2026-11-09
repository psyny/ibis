import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict

NotificationBox = Literal["inbox", "deleted"]


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: Optional[uuid.UUID] = None
    type: str
    kind: str
    title: str
    body: Optional[str] = None
    data: dict[str, Any]
    task_id: Optional[uuid.UUID] = None
    viewed_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    created_at: datetime


class NotificationBar(BaseModel):
    """Latest unread notes for the bar under the top bar, plus the unread count (menu badge)."""

    items: list[NotificationRead]
    unviewed_count: int
