"""Pydantic API schemas for founders and startups (request/response models)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import (
    CasteCategory,
    EntityType,
    Gender,
    RegSubtype,
    StartupStage,
    Terrain,
    VerificationStatus,
)


class FounderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(pattern=r"^\+?[1-9]\d{1,14}$")
    date_of_birth: date
    gender: Gender
    state: str
    district: str
    city: str
    pincode: str | None = None
    highest_qualification: str | None = None
    institution: str | None = None
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    first_graduate: bool = False
    caste_category: CasteCategory | None = None
    discoverable: bool = False


class FounderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    founder_id: uuid.UUID
    name: str
    email: EmailStr
    state: str
    district: str
    city: str
    first_graduate: bool
    caste_category: CasteCategory | None = None


class StartupCreate(BaseModel):
    startup_name: str = Field(min_length=1, max_length=255)
    entity_type: EntityType
    domain: str
    stage: StartupStage
    cin_number: str | None = None
    dpiit_number: str | None = None
    gstin: str | None = None
    incorporation_date: date | None = None
    employee_count: int = Field(default=0, ge=0)
    monthly_revenue: Decimal = Field(default=Decimal("0"), ge=0)
    terrain: Terrain | None = None
    reg_subtype: RegSubtype | None = None


class StartupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    startup_id: uuid.UUID
    founder_id: uuid.UUID
    startup_name: str
    entity_type: EntityType
    domain: str
    stage: StartupStage
    verification_status: VerificationStatus


class CompletenessRead(BaseModel):
    score: int
    tier: str
    missing_fields: list[str]
    verified_fields: list[str]
