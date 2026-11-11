import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# disconnected: no number linked; qr: waiting for the QR to be scanned; unavailable: service down
ConnectionStatus = Literal["off", "unavailable", "disconnected", "connecting", "qr", "connected"]


class WhatsAppStatus(BaseModel):
    """The household's WhatsApp link. `off` = this server has no WhatsApp service configured."""

    status: ConnectionStatus
    qr: Optional[str] = None  # data URL of the QR code to scan (status "qr")
    phone: Optional[str] = None  # the linked number
    name: Optional[str] = None  # its WhatsApp name
    error: Optional[str] = None


class AvailableGroup(BaseModel):
    """A group the linked number is in."""

    jid: str
    name: str
    participants: int = 0
    added: bool = False  # already one of the household's groups


class WhatsAppGroupCreate(BaseModel):
    jid: str = Field(..., min_length=5, max_length=100, pattern=r"^[0-9-]+@g\.us$")
    name: str = Field(..., min_length=1, max_length=200)


class WhatsAppGroupUpdate(BaseModel):
    is_active: bool


class WhatsAppGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    jid: str
    name: str
    is_active: bool


class WhatsAppTest(BaseModel):
    """Send a test message to one of the household's groups or to a member's number (exactly one)."""

    group_id: Optional[uuid.UUID] = None
    member_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def one_target(self):
        if (self.group_id is None) == (self.member_id is None):
            raise ValueError("Give either group_id or member_id")
        return self


class OutgoingMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: str
    recipient_label: str
    text: str
    status: str
    attempts: int
    last_error: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime


class WhatsAppTestResult(BaseModel):
    """Who the sample payment reminder pays (None: nobody in the household has a usable PIX key)."""

    payment_receiver: Optional[str] = None
