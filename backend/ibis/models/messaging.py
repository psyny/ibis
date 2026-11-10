import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy import true as sa_true
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base

CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_EMAIL = "email"

STATUS_PENDING = "pending"
STATUS_SENT = "sent"
STATUS_FAILED = "failed"  # gave up after MAX_ATTEMPTS


class WhatsAppGroup(Base):
    """A WhatsApp group the household's connected number is in, picked by a manager ("Household groups").

    Groups are stored by their WhatsApp id (`jid`, e.g. "1203634...@g.us"): names can change and repeat,
    the id doesn't. `name` is a copy for display, refreshed whenever the group list is loaded.
    """

    __tablename__ = "whatsapp_groups"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jid: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Paused groups get nothing, without losing the setup
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa_true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("household_id", "jid", name="uq_whatsapp_groups_household_jid"),)


class OutgoingMessage(Base):
    """A message waiting to go out (or already sent) on WhatsApp or email.

    Producers only add rows; a loop in the API process delivers them, so a slow or offline
    WhatsApp service never slows down a request. Kept as a log (Settings -> WhatsApp shows the latest).
    """

    __tablename__ = "outgoing_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(10), nullable=False)
    # WhatsApp: a group jid or a phone number (digits with country code); email: an address
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    # Who it is for, for the log (a person's or group's name)
    recipient_label: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default=STATUS_PENDING, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
