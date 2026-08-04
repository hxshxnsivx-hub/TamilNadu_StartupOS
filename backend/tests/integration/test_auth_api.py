"""Integration tests for the auth endpoints.

Requires a reachable PostgreSQL (schema is created from metadata for the test).
Skipped automatically when no database is available, so the default unit run
stays green without infrastructure.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from app.db.session import engine
from app.main import app
from app.models import Base
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def client():
    # Skip cleanly if there is no database to talk to.
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # pragma: no cover - infra-dependent
        pytest.skip(f"database unavailable: {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_register_login_refresh_me(client: AsyncClient):
    creds = {"email": "founder@example.com", "password": "s3cret-pass"}

    r = await client.post("/api/v1/auth/register", json=creds)
    assert r.status_code == 201
    tokens = r.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]

    # duplicate registration is rejected with the standard envelope
    r_dup = await client.post("/api/v1/auth/register", json=creds)
    assert r_dup.status_code == 409
    assert r_dup.json()["error_code"] == "EMAIL_TAKEN"

    r_login = await client.post("/api/v1/auth/login", json=creds)
    assert r_login.status_code == 200
    access = r_login.json()["access_token"]

    r_me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r_me.status_code == 200
    assert r_me.json()["email"] == creds["email"]

    r_refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": r_login.json()["refresh_token"]}
    )
    assert r_refresh.status_code == 200
    assert r_refresh.json()["access_token"]


async def test_bad_credentials_and_unauth(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "password1"})
    r = await client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["error_code"] == "INVALID_CREDENTIALS"

    r_noauth = await client.get("/api/v1/auth/me")
    assert r_noauth.status_code == 401
