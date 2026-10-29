import datetime as dt
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.category import Category
from models.member import HouseholdMember

# Where a cost came from. Future integrations (WhatsApp, voice/AI) get their own value.
SOURCE_WEB = "web"
SOURCE_RECURRING = "recurring"


def _member_link_table(name: str, owner_table: str, owner_column: str) -> Table:
    return Table(
        name,
        Base.metadata,
        Column(owner_column, Uuid, ForeignKey(f"{owner_table}.id", ondelete="CASCADE"), primary_key=True),
        Column("member_id", Uuid, ForeignKey("household_members.id", ondelete="CASCADE"), primary_key=True),
    )


cost_payers = _member_link_table("cost_payers", "costs", "cost_id")
cost_coverers = _member_link_table("cost_coverers", "costs", "cost_id")
recurring_cost_payers = _member_link_table("recurring_cost_payers", "recurring_costs", "recurring_cost_id")
recurring_cost_coverers = _member_link_table("recurring_cost_coverers", "recurring_costs", "recurring_cost_id")


class Cost(Base):
    __tablename__ = "costs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    month_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("household_months.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default=SOURCE_WEB)
    recurring_cost_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("recurring_costs.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Set by the app with microseconds: it orders costs added on the same day.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(dt.timezone.utc), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped[Optional[Category]] = relationship(Category, lazy="joined")
    payers: Mapped[list[HouseholdMember]] = relationship(secondary=cost_payers, lazy="selectin")
    coverers: Mapped[list[HouseholdMember]] = relationship(secondary=cost_coverers, lazy="selectin")


class RecurringCost(Base):
    """A cost copied into every new month: the household's "starting state"."""

    __tablename__ = "recurring_costs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped[Optional[Category]] = relationship(Category, lazy="joined")
    payers: Mapped[list[HouseholdMember]] = relationship(secondary=recurring_cost_payers, lazy="selectin")
    coverers: Mapped[list[HouseholdMember]] = relationship(secondary=recurring_cost_coverers, lazy="selectin")
