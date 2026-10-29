"""Sign-in tokens.

Sessions are "sliding": a token lives JWT_EXPIRATION_HOURS (90 days by default) and the
API hands out a fresh one (X-Refreshed-Token header) once it is older than
JWT_REFRESH_AFTER_HOURS. So anyone who opens the app at least once every 90 days stays
signed in. Each token carries the user's token_version; bumping it (password change,
"sign out everywhere") makes all older tokens invalid.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from infrastructure.config.settings import settings


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    token_version: int
    issued_at: datetime

    def needs_refresh(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return now - self.issued_at >= timedelta(hours=settings.jwt_refresh_after_hours)


def create_access_token(user_id: uuid.UUID, token_version: int = 0, issued_at: Optional[datetime] = None) -> str:
    """Create a JWT for a user. `issued_at` is only overridden in tests."""
    issued = issued_at or datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "ver": token_version,
        "iat": int(issued.timestamp()),
        "exp": issued + timedelta(hours=settings.jwt_expiration_hours),
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[TokenClaims]:
    """Return the token's claims, or None if it is invalid or expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return TokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            token_version=int(payload.get("ver", 0)),
            issued_at=datetime.fromtimestamp(int(payload.get("iat", 0)), tz=timezone.utc),
        )
    except (JWTError, ValueError, KeyError, TypeError):
        return None
