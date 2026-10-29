from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.roles import Role
from infrastructure.security.jwt_handler import create_access_token
from infrastructure.security.password_hasher import verify_password
from models.household import Household
from models.user import User
from repositories.member_repository import MemberRepository
from repositories.user_repository import UserRepository
from schemas.user_schemas import MeResponse, MyHousehold, UserRead
from services.errors import AuthenticationError, PermissionDeniedError


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.members = MemberRepository(db)

    def login(self, login_name: str, password: str) -> tuple[str, User]:
        user = self.users.get_by_login_name(login_name)
        if user is None:
            # Bootstrap: the very first login creates the app admin (same as qdra).
            if self.users.count_all() == 0:
                user = self.users.create(login_name, password, login_name, is_admin=True)
                self.db.commit()
                print(f"Created first (admin) user: {login_name}")
            else:
                raise AuthenticationError("Invalid login or password")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid login or password")
        if not self.can_sign_in(user):
            raise PermissionDeniedError("Your account is disabled")

        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        return create_access_token(user.id, user.token_version), user

    def sign_out_everywhere(self, user: User) -> str:
        """Invalidate every token of this user. Returns a new token for the current device."""
        user.token_version += 1
        self.db.commit()
        return create_access_token(user.id, user.token_version)

    def can_sign_in(self, user: User) -> bool:
        """Disabled users can't sign in. A non-admin whose memberships are all disabled is disabled too."""
        if not user.is_active:
            return False
        if user.is_admin:
            return True
        return any(m.is_active for m in self.members.list_for_user(user.id))

    def me(self, user: User) -> MeResponse:
        households: list[MyHousehold] = []
        memberships = {m.household_id: m for m in self.members.list_for_user(user.id) if m.is_active}
        if user.is_admin:
            for household in self.db.scalars(select(Household).order_by(Household.name)):
                member = memberships.get(household.id)
                households.append(
                    MyHousehold(
                        id=household.id,
                        name=household.name,
                        currency=household.currency,
                        role=Role.MANAGER.value,
                        member_id=member.id if member else None,
                    )
                )
        else:
            for member in memberships.values():
                household = self.db.get(Household, member.household_id)
                households.append(
                    MyHousehold(
                        id=household.id,
                        name=household.name,
                        currency=household.currency,
                        role=member.role,
                        member_id=member.id,
                    )
                )
            households.sort(key=lambda h: h.name.casefold())

        return MeResponse(
            **UserRead.model_validate(user).model_dump(),
            transfer_qr=user.transfer_qr,
            households=households,
        )
