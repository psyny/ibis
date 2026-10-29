import uuid

from sqlalchemy.orm import Session

from infrastructure.config.settings import settings
from infrastructure.security.password_hasher import verify_password
from models.user import User
from repositories.user_repository import UserRepository
from schemas.user_schemas import AdminUserCreate, AdminUserUpdate, PasswordChange, ProfileUpdate
from services.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def validate_qr_image(data_url: str) -> None:
    if not data_url.startswith("data:image/"):
        raise ValidationError("The QR code must be an image")
    if len(data_url) > settings.max_qr_image_kb * 1024 * 4 // 3:
        raise ValidationError(f"The QR image is too large (max {settings.max_qr_image_kb} KB)")


def apply_contact_fields(user: User, data) -> None:
    """Copy name/contact/bank fields that were sent in `data` onto the user."""
    fields = data.model_fields_set
    if "display_name" in fields and data.display_name:
        user.display_name = data.display_name.strip()
    if "email" in fields:
        user.email = _clean(data.email)
    if "whatsapp" in fields:
        user.whatsapp = _clean(data.whatsapp)
    if "bank_info_type" in fields and data.bank_info_type:
        user.bank_info_type = data.bank_info_type
    if "bank_info" in fields:
        user.bank_info = _clean(data.bank_info)


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    # --- Own account ----------------------------------------------------------
    def update_profile(self, user: User, data: ProfileUpdate) -> User:
        fields = data.model_fields_set
        apply_contact_fields(user, data)
        if "transfer_qr" in fields:
            if data.transfer_qr:
                validate_qr_image(data.transfer_qr)
                user.transfer_qr = data.transfer_qr
            else:
                user.transfer_qr = None
        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(self, user: User, data: PasswordChange) -> None:
        if not verify_password(data.current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")
        self.users.set_password(user, data.new_password)
        self.db.commit()

    # --- Admin ----------------------------------------------------------------
    def list_users(self) -> list[User]:
        return self.users.list_all()

    def create_user(self, data: AdminUserCreate) -> User:
        if self.users.get_by_login_name(data.login_name):
            raise ConflictError("This login is already taken")
        user = self.users.create(data.login_name, data.password, data.display_name, is_admin=data.is_admin)
        self.db.commit()
        return user

    def admin_update_user(self, actor: User, user_id: uuid.UUID, data: AdminUserUpdate) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        if user.id == actor.id and (data.is_admin is False or data.is_active is False):
            raise ValidationError("You can't remove your own admin access or disable yourself")
        if data.display_name:
            user.display_name = data.display_name.strip()
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.is_admin is not None:
            user.is_admin = data.is_admin
        if data.new_password:
            self.users.set_password(user, data.new_password)
        self.db.commit()
        self.db.refresh(user)
        return user
