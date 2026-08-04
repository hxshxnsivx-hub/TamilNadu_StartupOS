"""Legal verification endpoint (Task 2.1)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.verification.gateway import get_gateway

router = APIRouter(prefix="/api/v1/verify", tags=["verification"])


class VerifyIn(BaseModel):
    value: str = Field(min_length=1, max_length=40)


class VerificationOut(BaseModel):
    kind: str
    value_masked: str
    verified: bool
    status: str
    source: str
    reason: str | None = None
    details: dict[str, Any] = {}


@router.post("/{kind}", response_model=VerificationOut)
async def verify(kind: str, body: VerifyIn) -> VerificationOut:
    """Verify a legal identifier (kind ∈ cin | gstin | pan | dpiit)."""
    r = await get_gateway().verify(kind, body.value)
    return VerificationOut(
        kind=r.kind,
        value_masked=r.value_masked,
        verified=r.verified,
        status=r.status,
        source=r.source,
        reason=r.reason,
        details=r.details,
    )
