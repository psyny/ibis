import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from domain.languages import DEFAULT_LANGUAGE, LanguageCode
from domain.roles import Role
from schemas.user_schemas import BankInfoType


class PaymentTaskSettings(BaseModel):
    """What happens when a month closes: a "pay" task for each person who owes money."""

    enabled: bool = True
    # Due this many days after the month closes (always counted from the close)
    due_days: int = Field(3, ge=0, le=365)
    # Turns yellow (and can notify) this many days before it is due
    warn_days: int = Field(3, ge=0, le=365)
    # Same notify options as a task
    notify_expiring: bool = False
    notify_expired: bool = False
    notify_expiring_whatsapp: bool = False
    notify_expiring_email: bool = False
    notify_expiring_groups: bool = False
    notify_expired_whatsapp: bool = False
    notify_expired_email: bool = False
    notify_expired_groups: bool = False


class HouseholdCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    currency: str = Field("USD", min_length=3, max_length=3)
    timezone: str = Field("UTC", min_length=1, max_length=64)
    auto_close_days: Optional[int] = Field(None, ge=0, le=365)
    shield_costs_from_guests: bool = False
    language: LanguageCode = DEFAULT_LANGUAGE


class HouseholdUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    timezone: Optional[str] = Field(None, min_length=1, max_length=64)
    auto_close_days: Optional[int] = Field(None, ge=0, le=365)
    # auto_close_days=None is ambiguous in a PATCH-like body; use this to turn it off.
    disable_auto_close: bool = False
    shield_costs_from_guests: Optional[bool] = None
    language: Optional[LanguageCode] = None
    # Replaces all the month-close payment task settings at once
    payment_task: Optional[PaymentTaskSettings] = None


class HouseholdPermissions(BaseModel):
    can_add_cost: bool
    can_manage: bool
    # Add tasks and manage recurring tasks (managers and residents)
    can_add_task: bool = False


class HouseholdRead(BaseModel):
    id: uuid.UUID
    name: str
    currency: str
    timezone: str
    auto_close_days: Optional[int] = None
    shield_costs_from_guests: bool = False
    language: str = DEFAULT_LANGUAGE
    payment_task: PaymentTaskSettings = PaymentTaskSettings()
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
