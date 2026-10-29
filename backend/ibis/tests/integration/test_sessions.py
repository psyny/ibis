"""Sliding sessions: tokens renew as they are used; password changes sign out other devices."""
import uuid
from datetime import datetime, timedelta, timezone

from infrastructure.config.settings import settings
from infrastructure.security.jwt_handler import create_access_token, decode_token
from tests.conftest import ADMIN_LOGIN, ADMIN_PASSWORD, auth

HEADER = "X-Refreshed-Token"


def _admin_id(client, headers) -> uuid.UUID:
    return uuid.UUID(client.get("/api/auth/me", headers=headers).json()["id"])


def test_token_lasts_90_days_by_default():
    issued = datetime.now(timezone.utc)
    token = create_access_token(uuid.uuid4(), 0, issued_at=issued)
    assert settings.jwt_expiration_hours == 24 * 90
    assert decode_token(token) is not None
    expired = create_access_token(uuid.uuid4(), 0, issued_at=issued - timedelta(days=91))
    assert decode_token(expired) is None


def test_fresh_token_is_not_renewed(client, admin):
    response = client.get("/api/auth/me", headers=admin)
    assert response.status_code == 200
    assert HEADER not in response.headers


def test_old_token_is_renewed_on_use(client, admin):
    user_id = _admin_id(client, admin)
    old = create_access_token(user_id, 0, issued_at=datetime.now(timezone.utc) - timedelta(days=60))

    response = client.get("/api/auth/me", headers=auth(old))
    assert response.status_code == 200
    renewed = response.headers[HEADER]
    claims = decode_token(renewed)
    assert claims.user_id == user_id and not claims.needs_refresh()
    # The renewal header is also sent on other endpoints and exposed to the browser via CORS
    assert client.get("/api/admin/households", headers=auth(old)).headers.get(HEADER)
    cors = client.get("/api/auth/me", headers={**auth(old), "Origin": "http://localhost:3000"})
    assert HEADER.lower() in cors.headers.get("access-control-expose-headers", "").lower()


def test_password_change_signs_out_other_devices(client, admin, login):
    other_device = login(ADMIN_LOGIN, ADMIN_PASSWORD)
    response = client.post(
        "/api/me/password", json={"current_password": ADMIN_PASSWORD, "new_password": "new-pass-123"}, headers=admin
    )
    assert response.status_code == 200
    this_device = auth(response.json()["token"])

    assert client.get("/api/auth/me", headers=this_device).status_code == 200
    assert client.get("/api/auth/me", headers=other_device).status_code == 401
    assert client.get("/api/auth/me", headers=admin).status_code == 401  # the old token of this device too


def test_sign_out_everywhere(client, admin, login):
    other_device = login(ADMIN_LOGIN, ADMIN_PASSWORD)
    new_token = client.post("/api/me/sign-out-everywhere", headers=admin).json()["token"]
    assert client.get("/api/auth/me", headers=auth(new_token)).status_code == 200
    assert client.get("/api/auth/me", headers=other_device).status_code == 401


def test_manager_password_reset_signs_out_that_person(client, admin, login):
    household = client.post("/api/admin/households", json={"name": "Home"}, headers=admin).json()
    hid = household["id"]
    member = client.post(
        f"/api/households/{hid}/members",
        json={"login_name": "zed", "display_name": "Zed", "password": "pass1234", "role": "resident"},
        headers=admin,
    ).json()
    zed = login("zed", "pass1234")
    assert client.post(f"/api/households/{hid}/members/{member['id']}/password", json={"new_password": "reset-123"}, headers=admin).status_code == 204
    assert client.get("/api/auth/me", headers=zed).status_code == 401
    login("zed", "reset-123")  # the new password works
