import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from db.session import get_db
from domain.roles import MIN_ROLE_VIEW, Role, has_role
from infrastructure.security.jwt_handler import create_access_token, decode_token
from models.household import Household
from models.user import User
from repositories.member_repository import MemberRepository
from services.context import HouseholdContext

security = HTTPBearer(auto_error=False)


REFRESHED_TOKEN_HEADER = "X-Refreshed-Token"


def get_current_user(
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """The signed-in user. Also renews the token (sliding session) when it is getting old."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    claims = decode_token(credentials.credentials)
    user = db.get(User, claims.user_id) if claims else None
    if user is None or not user.is_active or claims.token_version != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session has ended. Please sign in again.")
    if claims.needs_refresh():
        response.headers[REFRESHED_TOKEN_HEADER] = create_access_token(user.id, user.token_version)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def household_context(minimum: Role = MIN_ROLE_VIEW):
    """Dependency factory: resolves the household from the path and checks the caller's role."""

    def dependency(
        household_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> HouseholdContext:
        household = db.get(Household, household_id)
        if household is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")

        member = MemberRepository(db).get_for_user(household.id, user.id)
        if user.is_admin:
            role = Role.MANAGER
        elif member is None or not member.is_active:
            # Disabled members lose access (but stay in the history)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this household")
        else:
            role = Role(member.role)

        if not has_role(role, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"This action requires the '{minimum.value}' role"
            )
        return HouseholdContext(
            user=user, household=household, member=member if member and member.is_active else None, role=role
        )

    return dependency
