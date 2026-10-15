"""The registered-startup journey: which registrations apply, why, and in what order.

    POST /api/v1/journey   facts (+ domain, + steps already done) -> ordered steps

Stateless for now: the client sends what is done. Saving it per founder comes
with the profile endpoints.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.journey.engine import journey
from app.planner import registry

router = APIRouter(prefix="/api/v1", tags=["journey"])


class JourneyFacts(BaseModel):
    entity: Literal["none", "proprietorship", "partnership", "llp", "pvt_ltd", "opc"] | None = None
    registered: bool | None = None
    years_since_incorporation: int | None = Field(default=None, ge=0, le=100)
    turnover_lakh: float | None = Field(default=None, ge=0)
    goods: bool | None = None
    services: bool | None = None
    interstate: bool | None = None
    sells_online: bool | None = None
    exports: bool | None = None
    innovative: bool | None = None
    has_brand: bool | None = None
    has_premises: bool | None = None
    employees: int | None = Field(default=None, ge=0)
    raise_equity: bool | None = None
    district: str | None = Field(default=None, pattern=r"^[a-z]+$")


class JourneyIn(BaseModel):
    facts: JourneyFacts = Field(default_factory=JourneyFacts)
    domain_id: str | None = None
    done: list[str] = Field(default_factory=list, max_length=50)


@router.post("/journey")
async def registration_journey(body: JourneyIn) -> dict:
    """Every registration step with its status, reason, documents and official link."""
    if body.domain_id and body.domain_id not in registry.load()["domains"]:
        raise HTTPException(status_code=404, detail=f"Unknown domain {body.domain_id}")
    return journey(body.facts.model_dump(), body.domain_id, body.done)
