from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from infrastructure.security.jwt_handler import create_access_token
from models.user import User
from schemas.user_schemas import LoginRequest, LoginResponse, MeResponse, PasswordChange, ProfileUpdate, UserRead
from services.auth_service import AuthService
from services.errors import AuthenticationError
from services.user_service import UserService

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Returns a JWT. The very first login on an empty database creates the admin."""
    token, user = AuthService(db).login(request.login, request.password)
    return LoginResponse(token=token, user=UserRead.model_validate(user))


@router.get("/auth/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = AuthService(db)
    if not service.can_sign_in(user):
        raise AuthenticationError("Your account is disabled")
    return service.me(user)


@router.put("/me", response_model=MeResponse)
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    UserService(db).update_profile(user, data)
    return AuthService(db).me(user)


class TokenResponse(BaseModel):
    token: str


@router.post("/me/password", response_model=TokenResponse)
def change_password(data: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Changes the password and signs out every other device. Returns a new token for this one."""
    UserService(db).change_password(user, data)
    return TokenResponse(token=create_access_token(user.id, user.token_version))


@router.post("/me/sign-out-everywhere", response_model=TokenResponse)
def sign_out_everywhere(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Signs out every other device (e.g. a lost phone). Returns a new token for this one."""
    return TokenResponse(token=AuthService(db).sign_out_everywhere(user))
