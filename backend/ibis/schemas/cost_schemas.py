import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class CostCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=200)
    category_id: Optional[uuid.UUID] = None
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    date: date
    payer_ids: list[uuid.UUID] = Field(..., min_length=1)
    coverer_ids: list[uuid.UUID] = Field(..., min_length=1)


class CostUpdate(CostCreate):
    pass


class CostRead(BaseModel):
    id: uuid.UUID
    description: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    amount: float
    date: date
    payer_ids: list[uuid.UUID]
    coverer_ids: list[uuid.UUID]
    paid_share: float
    cover_share: float
    source: str
    recurring_cost_id: Optional[uuid.UUID] = None
    created_by_user_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    can_edit: bool = False


class RecurringCostCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=200)
    category_id: Optional[uuid.UUID] = None
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    day_of_month: int = Field(1, ge=1, le=31)
    payer_ids: list[uuid.UUID] = Field(..., min_length=1)
    coverer_ids: list[uuid.UUID] = Field(..., min_length=1)
    is_active: bool = True


class RecurringCostUpdate(RecurringCostCreate):
    pass


class RecurringCostRead(BaseModel):
    id: uuid.UUID
    description: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    amount: float
    day_of_month: int
    payer_ids: list[uuid.UUID]
    coverer_ids: list[uuid.UUID]
    is_active: bool
