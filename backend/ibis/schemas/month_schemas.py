import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from schemas.catalog_schemas import CategoryRead
from schemas.cost_schemas import CostRead
from schemas.household_schemas import MemberRead


class MonthCreate(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)


class MonthRead(BaseModel):
    id: uuid.UUID
    year: int
    month: int
    status: str
    closed_at: Optional[datetime] = None
    auto_close_on: Optional[date] = None
    cost_count: int = 0
    total: float = 0


class BalanceRead(BaseModel):
    member_id: uuid.UUID
    paid: float
    covered: float
    net: float  # positive = receives, negative = pays


class TransferRead(BaseModel):
    from_member_id: uuid.UUID
    to_member_id: uuid.UUID
    amount: float


class CategoryTotalRead(BaseModel):
    category_id: Optional[uuid.UUID] = None
    name: str
    color: Optional[str] = None
    total: float


class MonthSummary(BaseModel):
    month: MonthRead
    currency: str
    total: float
    members: list[MemberRead]
    balances: list[BalanceRead]
    transfers: list[TransferRead]
    category_totals: list[CategoryTotalRead]
    categories: list[CategoryRead]
    costs: list[CostRead]
    can_add_cost: bool
    can_manage: bool
