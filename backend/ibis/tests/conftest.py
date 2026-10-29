"""Shared fixtures.

Tests run against TEST_DATABASE_URL (default: a throw-away SQLite file), so
they work without Docker. Point it at Postgres to test against the real thing:
    TEST_DATABASE_URL=postgresql://ibis:ibis@localhost:5432/ibis_test
"""
import os
import tempfile
from typing import Callable

import pytest

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "sqlite:///" + os.path.join(tempfile.gettempdir(), "ibis_test.sqlite3").replace("\\", "/")
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL  # must happen before importing the app

from fastapi.testclient import TestClient  # noqa: E402

import models  # noqa: E402,F401
from db.base import Base  # noqa: E402
from db.session import engine  # noqa: E402
from main import app  # noqa: E402

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin-pass"


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def login(client) -> Callable[[str, str], dict]:
    def _login(login_name: str, password: str) -> dict:
        response = client.post("/api/auth/login", json={"login": login_name, "password": password})
        assert response.status_code == 200, response.text
        return auth(response.json()["token"])

    return _login


@pytest.fixture()
def admin(login) -> dict:
    """Headers of the bootstrap admin (first login creates it)."""
    return login(ADMIN_LOGIN, ADMIN_PASSWORD)
