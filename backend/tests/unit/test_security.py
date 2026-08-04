"""Unit tests for password hashing and JWT tokens (no DB required)."""

from datetime import timedelta

import pytest
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("s3cret-pass")
    assert h != "s3cret-pass"
    assert verify_password("s3cret-pass", h) is True
    assert verify_password("wrong", h) is False


def test_access_token_carries_type_and_subject():
    tok = create_access_token("user-123")
    payload = decode_token(tok, expected_type="access")
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert "jti" in payload and "exp" in payload


def test_refresh_token_type():
    payload = decode_token(create_refresh_token("u1"), expected_type="refresh")
    assert payload["type"] == "refresh"


def test_wrong_token_type_rejected():
    access = create_access_token("u1")
    with pytest.raises(AppError) as ei:
        decode_token(access, expected_type="refresh")
    assert ei.value.error_code == "WRONG_TOKEN_TYPE"
    assert ei.value.status_code == 401


def test_expired_token_rejected():
    expired = create_access_token("u1", expires_delta=timedelta(seconds=-1))
    with pytest.raises(AppError) as ei:
        decode_token(expired)
    assert ei.value.error_code == "TOKEN_EXPIRED"


def test_tampered_token_rejected():
    tok = create_access_token("u1")
    with pytest.raises(AppError) as ei:
        decode_token(tok + "x")
    assert ei.value.error_code == "INVALID_TOKEN"
