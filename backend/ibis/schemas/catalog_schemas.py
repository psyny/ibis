import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=20)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=20)
    is_archived: Optional[bool] = None


class CategoryRead(BaseModel):
    id: uuid.UUID
    name: str
    color: Optional[str] = None
    is_archived: bool


class PresetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category_id: Optional[uuid.UUID] = None
    default_amount: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)


class PresetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category_id: Optional[uuid.UUID] = None
    default_amount: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    clear_category: bool = False
    clear_default_amount: bool = False


class PresetRead(BaseModel):
    id: uuid.UUID
    name: str
    category_id: Optional[uuid.UUID] = None
    default_amount: Optional[float] = None
