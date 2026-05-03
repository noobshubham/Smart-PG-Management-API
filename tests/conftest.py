"""Shared pytest fixtures.

Each test gets:
- A fresh in-memory SQLite engine with `Base.metadata.create_all`.
- `get_db` overridden to use that engine's session.
- `get_ai_provider` and `get_whatsapp_client` overridden to fakes.
- A registered owner + bearer token via `auth_client`.

Production singletons are never touched.
"""
from __future__ import annotations

import os

# Set sane defaults BEFORE app import so settings validation passes.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test-verify")

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.db import get_db  # noqa: E402
from app.core.models import Base  # noqa: E402
from app.integrations.ai import get_ai_provider  # noqa: E402
from app.integrations.whatsapp import get_whatsapp_client  # noqa: E402
from app.main import app  # noqa: E402
from tests.fakes import FakeAIProvider, FakeWhatsAppClient  # noqa: E402


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def fake_ai() -> FakeAIProvider:
    return FakeAIProvider()


@pytest.fixture
def fake_whatsapp() -> FakeWhatsAppClient:
    return FakeWhatsAppClient()


@pytest.fixture
def client(db_engine, fake_ai, fake_whatsapp) -> Generator[TestClient, None, None]:
    SessionLocal = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False, expire_on_commit=False
    )

    def _override_get_db() -> Generator[Session, None, None]:
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_ai_provider] = lambda: fake_ai
    app.dependency_overrides[get_whatsapp_client] = lambda: fake_whatsapp

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _register_and_login(
    client: TestClient,
    *,
    pg_name: str,
    phone_number: str,
    password: str = "supersecret",
) -> tuple[int, str]:
    r = client.post(
        "/auth/register",
        json={
            "pg_name": pg_name,
            "owner_name": pg_name + " Owner",
            "phone_number": phone_number,
            "password": password,
        },
    )
    assert r.status_code == 201, r.text
    owner_id = r.json()["id"]

    r = client.post(
        "/auth/login",
        json={"phone_number": phone_number, "password": password},
    )
    assert r.status_code == 200, r.text
    return owner_id, r.json()["access_token"]


@pytest.fixture
def owner_token(client: TestClient) -> tuple[int, str]:
    return _register_and_login(client, pg_name="Sunrise PG", phone_number="911000000001")


@pytest.fixture
def auth_headers(owner_token) -> dict[str, str]:
    _owner_id, token = owner_token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_owner_token(client: TestClient) -> tuple[int, str]:
    return _register_and_login(client, pg_name="Lakeview PG", phone_number="911000000002")
