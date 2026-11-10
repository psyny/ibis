import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Uuid, func
from sqlalchemy import false as sa_false
from sqlalchemy import true as sa_true
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Household(Base):
    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    # Interface language for everyone in the household (see domain/languages.py)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en", server_default="en")
    # Days after a month ends before it closes automatically. None = never.
    auto_close_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Guests only see costs, transfers and totals that involve them (no category breakdown).
    shield_costs_from_guests: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa_false()
    )

    # When a month closes: a "pay" task for each person who owes money (see TaskService.month_closed)
    payment_task_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa_true())
    # Due this many days after the month closes; turns yellow (expiring) this many days before that
    payment_task_due_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    payment_task_warn_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    # Same notify options as any task (models.task.NOTIFY_FLAGS), with a "payment_task_" prefix
    payment_task_notify_expiring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())
    payment_task_notify_expired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())
    payment_task_notify_expiring_whatsapp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())
    payment_task_notify_expiring_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())
    payment_task_notify_expiring_groups: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())
    payment_task_notify_expired_whatsapp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())
    payment_task_notify_expired_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())
    payment_task_notify_expired_groups: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
