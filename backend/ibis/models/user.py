import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Bumped to sign the user out on every device (password change, "sign out everywhere").
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # Account / payment info shown to other household members
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # How to pay this person. bank_info_type is "pix" (bank_info = PIX key, used to
    # generate payment QR codes) or "other" (free text, e.g. bank account details).
    bank_info_type: Mapped[str] = mapped_column(String(20), nullable=False, default="pix", server_default="pix")
    bank_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transfer_qr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # image data URL

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
