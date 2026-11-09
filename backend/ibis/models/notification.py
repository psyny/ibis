import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base

# Only notes for now: viewed (read) and deleted. To-dos live in household tasks (models/task.py).
TYPE_NOTE = "note"
NOTIFICATION_TYPES = (TYPE_NOTE,)

# What a notification is about. The frontend renders known kinds in the user's language
# (from `data`) and falls back to `title`/`body` (English) for anything else.
KIND_MONTH_PAYMENT = "month_payment"  # a payment task was created when a month closed
KIND_TASK_EXPIRING = "task_expiring"  # a task is due soon
KIND_TASK_EXPIRED = "task_expired"  # a task is past its due date


class Notification(Base):
    """One item in a user's notification inbox.

    Notes are viewed (read) and can be deleted; deleting only sets `deleted_at`.
    `task_id` links to the household task the note is about (it opens that task).
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
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    # Groups notifications about the same thing (e.g. one closed month), so they can be replaced.
    group_key: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)
