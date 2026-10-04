"""Request/response models for the startup-ecosystem endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

District = Literal["chennai", "coimbatore", "madurai"]
Stage = Literal["idea", "pre_seed", "seed", "pre_series_a", "series_a", "growth"]


class ZoneOut(BaseModel):
    id: str
    district: str
    name: str
    peak_pin: str
    pins: list[str]
    lat: float
    lon: float
    peak_z: float
    layers: dict[str, int]
    sectors: dict[str, int]
    specialisations: list[tuple[str, float]]


class ZonesOut(BaseModel):
    district: str
    link_km: float
    pins_total: int
    hot_pins: int
    zones: list[ZoneOut]
    method: str
    sources: dict[str, str]
    caveats: list[str]


class InvestorOut(BaseModel):
    slug: str
    name: str | None
    website: str | None
    summary: str | None
    about: str | None
    invests_in: str | None
    city: str | None
    asset_class: str
    serves_founders: bool
    instrument: str | None
    stages: list[str]
    sectors: list[str]
    generalist: bool
    ticket_lakh: list[float] | None
    source_url: str


class ReachOut(BaseModel):
    status: str
    pitch_url: str | None = None
    evidence: list[dict] = []
    checked: str | None = None


class InvestorMatchOut(BaseModel):
    investor: InvestorOut
    fit: int
    signals: dict[str, float]
    reachability: ReachOut
    why: list[str]


class InvestorRefusalOut(BaseModel):
    investor: InvestorOut
    reasons: list[str]


class PeerOut(BaseModel):
    name: str | None
    website: str | None
    careers_url: str | None
    description: str | None
    sector_label: str | None
    stage: str | None
    tier: str | None
    area: str | None
    founded: str | None = None
    team_size: str | None = None
    total_funding: str | None = None
    latest_round: str | None = None
    km: float | None
    same_zone: bool
    hiring: bool
    source_url: str


class CompanyOut(BaseModel):
    cin: str
    name: str
    sector: str | None
    year: int | None
    paidup_lakh: float
    pin: str


class PlatformOut(BaseModel):
    id: str
    name: str
    agency: str
    benefit: str
    source_url: str


class FounderIn(BaseModel):
    sectors: list[str] = Field(min_length=1)
    stage: Stage
    district: District
    pin: str | None = Field(default=None, pattern=r"^[1-9]\d{5}$")
    ask_lakh: float | None = Field(default=None, gt=0)
    instrument: Literal["equity", "debt", "either"] = "either"
    dpiit: bool | None = None
    company_age_years: float | None = Field(default=None, ge=0, le=100)
    limit: int = Field(default=10, ge=1, le=50)


class IncubatorOut(BaseModel):
    id: str
    website: str | None = None
    name: str
    host: str
    district: str
    area: str
    pin: str
    sectors: list[str]
    stages: list[str]
    programmes: list[str]
    notes: str
    source_url: str
    confidence: str


class ProgrammeFitOut(BaseModel):
    name: str
    applies: Literal["yes", "check", "closed", "no", "support"]
    reason: str
    status: str | None = None


class TravelOut(BaseModel):
    km: float
    road_km: float
    minutes: int
    basis: str


class IntakeOut(BaseModel):
    status: str  # open | rolling | apply_page | closed | unknown | stale | no_website | ...
    checked: str
    website: str | None = None
    deadline: str | None = None
    apply_url: str | None = None
    evidence: list[dict] = []
    note: str | None = None


class IncubatorMatchOut(BaseModel):
    incubator: IncubatorOut
    fit: int
    signals: dict[str, float]
    programmes: list[ProgrammeFitOut]
    travel: TravelOut | None
    why: list[str]
    intake: IntakeOut | None = None


class IncubatorRefusalOut(BaseModel):
    incubator: IncubatorOut
    reasons: list[str]


class FounderZoneOut(BaseModel):
    zone: ZoneOut
    km: float
    founder_sector_lq: dict[str, float]


class SectorZoneOut(BaseModel):
    zone_id: str
    name: str
    lq: float


class EcosystemMatchOut(BaseModel):
    zone: FounderZoneOut | None
    sector_zones: list[SectorZoneOut]
    investors: list[InvestorMatchOut]
    refused: list[InvestorRefusalOut]
    platforms: list[PlatformOut]
    peers: list[PeerOut]
    companies: list[CompanyOut]
    company_counts: dict[str, int]
    incubators: list[IncubatorMatchOut]
    incubators_refused: list[IncubatorRefusalOut]
    note: str
