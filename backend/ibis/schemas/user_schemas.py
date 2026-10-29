import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# "pix": bank_info is a PIX key (used to generate payment QR codes). "other": free text.
BankInfoType = Literal["pix", "other"]


class LoginRequest(BaseModel):
    login: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    login_name: str
    display_name: str
    is_active: bool
    is_admin: bool
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    bank_info_type: str = "pix"
    bank_info: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class MyHousehold(BaseModel):
    id: uuid.UUID
    name: str
    currency: str
    role: str
    member_id: Optional[uuid.UUID] = None  # None when an admin views a household they don't belong to


class MeResponse(UserRead):
    transfer_qr: Optional[str] = None
    households: list[MyHousehold] = []


class LoginResponse(BaseModel):
    token: str
    user: UserRead


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    whatsapp: Optional[str] = Field(None, max_length=50)
    bank_info_type: Optional[BankInfoType] = None
    bank_info: Optional[str] = Field(None, max_length=255)
    # Image data URL; send "" to remove
    transfer_qr: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4)


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=4)


class AdminUserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    new_password: Optional[str] = Field(None, min_length=4)


class AdminUserCreate(BaseModel):
    login_name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=4)
    is_admin: bool = False
