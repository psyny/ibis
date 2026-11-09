import datetime as dt
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy import false as sa_false
from sqlalchemy import true as sa_true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from domain.tasks import DEFAULT_WARN_DAYS
from models.cost import _member_link_table
from models.member import HouseholdMember

# What a task is about. Known kinds are shown in the UI language (from `data`); `title` is the fallback.
KIND_MANUAL = "manual"
KIND_RECURRING = "recurring"
KIND_MONTH_PAYMENT = "month_payment"

# Who a recurring task is assigned to when each copy is created
ASSIGN_SELECTED = "selected"  # the people picked in the definition
ASSIGN_EVERYONE = "everyone"  # active managers and residents at that moment
ASSIGN_EVERYONE_GUESTS = "everyone_guests"  # ...plus active guests
ASSIGN_MODES = (ASSIGN_SELECTED, ASSIGN_EVERYONE, ASSIGN_EVERYONE_GUESTS)

task_assignees = _member_link_table("task_assignees", "tasks", "task_id")
recurring_task_assignees = _member_link_table("recurring_task_assignees", "recurring_tasks", "recurring_task_id")


class TaskLabel(Base):
    """An entry of a household's task categories or locations (kind). Managers edit the lists;
    new households start with domain.task_labels defaults. Deleting one clears it from tasks."""

    __tablename__ = "task_labels"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Set on the defaults (e.g. "bills"), so they can be found even after being renamed
    key: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class _TaskSettings:
    """Fields shared by tasks and recurring task definitions (copied into each created task)."""

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # A task turns yellow (and can notify) this many days before it is due
    warn_days: Mapped[int] = mapped_column(Integer, nullable=False, default=DEFAULT_WARN_DAYS, server_default="3")
    notify_expiring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())
    notify_expired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())


class Task(_TaskSettings, Base):
    """A household to-do. Completed by any one of its assignees (or a resident/manager)."""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default=KIND_MANUAL)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("task_labels.id", ondelete="SET NULL"), nullable=True
    )
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("task_labels.id", ondelete="SET NULL"), nullable=True
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    # Groups system tasks about the same thing (e.g. one closed month), so they can be replaced.
    group_key: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    due_date: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)
    recurring_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("recurring_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # The scheduled date this copy of a recurring task was created for
    occurrence_date: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # When the "expiring" / "expired" notifications went out (reset when the due date changes)
    expiring_notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(dt.timezone.utc), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assignees: Mapped[list[HouseholdMember]] = relationship(secondary=task_assignees, lazy="selectin")
    category: Mapped[Optional[TaskLabel]] = relationship(TaskLabel, foreign_keys=[category_id], lazy="joined")
    location: Mapped[Optional[TaskLabel]] = relationship(TaskLabel, foreign_keys=[location_id], lazy="joined")

    # Two people opening the household at once can't create the same recurring copy twice
    __table_args__ = (UniqueConstraint("recurring_task_id", "occurrence_date", name="uq_tasks_recurring_occurrence"),)

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None


class RecurringTask(_TaskSettings, Base):
    """A task definition that creates a new task on each scheduled date (checked when the household is opened)."""

    __tablename__ = "recurring_tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("task_labels.id", ondelete="SET NULL"), nullable=True
    )
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("task_labels.id", ondelete="SET NULL"), nullable=True
    )
    start_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    interval: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit: Mapped[str] = mapped_column(String(10), nullable=False, default="week")
    # Each copy is due this many days after its scheduled date (0 = on the scheduled date)
    due_offset_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Skip a scheduled date while the previous copy is still not done
    wait_for_previous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa_true())
    assign_mode: Mapped[str] = mapped_column(String(20), nullable=False, default=ASSIGN_SELECTED)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa_true())
    # Latest scheduled date already handled (created, or skipped because the previous copy was open)
    last_occurrence_date: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assignees: Mapped[list[HouseholdMember]] = relationship(secondary=recurring_task_assignees, lazy="selectin")
    category: Mapped[Optional[TaskLabel]] = relationship(TaskLabel, foreign_keys=[category_id], lazy="joined")
    location: Mapped[Optional[TaskLabel]] = relationship(TaskLabel, foreign_keys=[location_id], lazy="joined")
