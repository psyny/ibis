import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base

TYPE_NOTE = "note"
TYPE_TASK = "task"
NOTIFICATION_TYPES = (TYPE_NOTE, TYPE_TASK)

# What a notification is about. The frontend renders known kinds in the user's language
# (from `data`) and falls back to `title`/`body` (English) for anything else.
KIND_MONTH_PAYMENT = "month_payment"


class Notification(Base):
    """One item in a user's notification inbox.

    Notes can be viewed and deleted; tasks can also be completed. Deleting only sets `deleted_at`.
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    household_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    # Groups notifications about the same thing (e.g. one closed month), so they can be replaced.
    group_key: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)

    @property
    def is_task(self) -> bool:
        return self.type == TYPE_TASK
