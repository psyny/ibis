import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from domain.roles import Role
from schemas.user_schemas import BankInfoType


class HouseholdCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    currency: str = Field("USD", min_length=3, max_length=3)
    timezone: str = Field("UTC", min_length=1, max_length=64)
    auto_close_days: Optional[int] = Field(None, ge=0, le=365)
    shield_costs_from_guests: bool = False


class HouseholdUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    timezone: Optional[str] = Field(None, min_length=1, max_length=64)
    auto_close_days: Optional[int] = Field(None, ge=0, le=365)
    # auto_close_days=None is ambiguous in a PATCH-like body; use this to turn it off.
    disable_auto_close: bool = False
    shield_costs_from_guests: Optional[bool] = None


class HouseholdPermissions(BaseModel):
    can_add_cost: bool
    can_manage: bool


class HouseholdRead(BaseModel):
    id: uuid.UUID
    name: str
    currency: str
    timezone: str
    auto_close_days: Optional[int] = None
    shield_costs_from_guests: bool = False
    today: date
    my_role: str
    my_member_id: Optional[uuid.UUID] = None
    permissions: HouseholdPermissions
    member_count: int = 0


class MemberRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    login_name: str
    display_name: str
    role: str
    is_active: bool
    is_participant: bool
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    bank_info_type: str = "pix"
    bank_info: Optional[str] = None
    has_transfer_qr: bool = False


class MemberDetail(MemberRead):
    transfer_qr: Optional[str] = None


class MemberCreate(BaseModel):
    login_name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=4)
    role: Role = Role.RESIDENT
    email: Optional[str] = Field(None, max_length=255)
    whatsapp: Optional[str] = Field(None, max_length=50)


class MemberUpdate(BaseModel):
    """Managers edit a person. Only the fields sent are changed ("" clears a text field)."""

    role: Optional[Role] = None
    is_active: Optional[bool] = None
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    whatsapp: Optional[str] = Field(None, max_length=50)
    bank_info_type: Optional[BankInfoType] = None
    bank_info: Optional[str] = Field(None, max_length=255)
