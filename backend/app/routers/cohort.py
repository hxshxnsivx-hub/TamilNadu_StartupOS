"""Cohorts: where an idea sits among others, and what a programme's founders share.

    POST /api/v1/cohort/reference   an idea -> similar TN startups and sector companies
    POST /api/v1/cohort/programme   session ids -> aggregates (consenting founders, 5+)
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.store import get_store
from app.cohort.programme import programme_cohort
from app.cohort.reference import reference_cohort

router = APIRouter(prefix="/api/v1/cohort", tags=["cohort"])


class ReferenceIn(BaseModel):
    idea: str = Field(min_length=10, max_length=2000)
    sector: str | None = Field(default=None, pattern=r"^[a-z_]+$")
    district: str | None = Field(default=None, pattern=r"^[a-z]+$")
    limit: int = Field(default=8, ge=1, le=25)


@router.post("/reference")
async def reference(body: ReferenceIn) -> dict:
    """Similar Tamil Nadu startups, the sector's registered companies, and what that means."""
    return reference_cohort(body.idea, body.sector, body.district, body.limit)


class ProgrammeIn(BaseModel):
    session_ids: list[str] = Field(min_length=1, max_length=500)


@router.post("/programme")
async def programme(body: ProgrammeIn) -> dict:
    """Aggregates across a programme's founders: only those who agreed, only 5 or more."""
    store = await get_store()
    sessions = [s for sid in dict.fromkeys(body.session_ids) if (s := await store.get(sid))]
    return {**programme_cohort(sessions), "sessions_found": len(sessions)}
