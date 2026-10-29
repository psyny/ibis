import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from infrastructure.security.password_hasher import hash_password
from models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, login_name: str, password: str, display_name: str, **fields) -> User:
        user = User(
            login_name=login_name.strip(),
            password_hash=hash_password(password),
            display_name=display_name.strip(),
            **fields,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_login_name(self, login_name: str) -> Optional[User]:
        """Case-insensitive lookup."""
        return self.db.scalar(select(User).where(func.lower(User.login_name) == login_name.strip().lower()))

    def list_all(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(func.lower(User.display_name))))

    def count_all(self) -> int:
        return self.db.scalar(select(func.count()).select_from(User)) or 0

    def set_password(self, user: User, password: str) -> None:
        """Change the password and sign the user out on every device."""
        user.password_hash = hash_password(password)
        user.token_version = (user.token_version or 0) + 1
