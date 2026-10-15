"""Startup-ecosystem endpoints — hotspot zones, investors and founder matching by district."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.ecosystem.incubators import load_incubators
from app.ecosystem.index import Ecosystem, get_ecosystem
from app.ecosystem.match import Founder, match
from app.ecosystem.taxonomy import SECTORS
from app.ecosystem.zones import Zone
from app.models.ecosystem_schemas import (
    CompanyOut,
    District,
    EcosystemMatchOut,
    FounderIn,
    FounderZoneOut,
    IncubatorMatchOut,
    IncubatorOut,
    IncubatorRefusalOut,
    InvestorMatchOut,
    InvestorOut,
    InvestorRefusalOut,
    PeerOut,
    PlatformOut,
    ReachOut,
    SectorZoneOut,
    ZoneOut,
    ZonesOut,
)

router = APIRouter(prefix="/api/v1/ecosystem", tags=["ecosystem"])

_METHOD = (
    "Activity per pin code = equal-weight index of MCA companies, startups and bank branches "
    "(log counts scaled within the district). Hotspots = Getis-Ord Gi* z ≥ 1.645 over pins within "
    "the district's link distance. Each hot pin joins the most active hot pin nearby until it "
    "reaches a local peak; a peak and its pins form a zone. Specialisations = sectors whose share "
    "in the zone is ≥ 1.25× the district's (location quotient), with at least 10 firms."
)
_MATCH_NOTE = (
    "Incubators are matched on sector focus, stage, estimated travel time and whether a "
    "programme run there can pay this founder now; scheme status comes from Vanigam's funding "
    "catalogue. "
    "Investors come from a hand-reviewed directory of Tamil Nadu-registered funds and angel "
    "networks; national funds investing in Tamil Nadu are not yet included — the platforms "
    "listed reach them. 'reachable' reflects the investor's own website on the date checked. "
    "Companies are from the MCA register (snapshot to early 2020), placed at registered office."
)


def _eco() -> Ecosystem:
    eco = get_ecosystem()
    if eco is None:
        raise HTTPException(status_code=503, detail="Ecosystem index not built")
    return eco


def _zone(z: Zone) -> ZoneOut:
    return ZoneOut(
        id=z.id,
        district=z.district,
        name=z.name,
        peak_pin=z.peak_pin,
        pins=z.pins,
        lat=z.lat,
        lon=z.lon,
        peak_z=z.peak_z,
        layers=z.layers,
        sectors=z.sectors,
        specialisations=z.specialisations,
    )


def _incubator(i: dict) -> IncubatorOut:
    return IncubatorOut(**{k: i.get(k) for k in IncubatorOut.model_fields})


def _investor(i: dict) -> InvestorOut:
    return InvestorOut(**{k: i.get(k) for k in InvestorOut.model_fields})


@router.get("/sectors")
async def sectors() -> dict[str, str]:
    """The sector vocabulary shared by companies, startups and investors."""
    return SECTORS


@router.get("/zones", response_model=ZonesOut)
async def zones(district: District = Query()) -> ZonesOut:
    """A district cut into hotspot zones, each with its activity and sector specialisations."""
    eco = _eco()
    dz = eco.districts[district]
    return ZonesOut(
        district=district,
        link_km=dz.link_km,
        pins_total=len(dz.pins),
        hot_pins=len(dz.zone_of),
        zones=[_zone(z) for z in dz.zones],
        method=_METHOD,
        sources=eco.meta.get("sources", {}),
        caveats=eco.meta.get("caveats", []),
    )


@router.get("/investors", response_model=list[InvestorOut])
async def investors(founders_only: bool = True) -> list[InvestorOut]:
    """Tamil Nadu-registered investors, classified; non-startup funds hidden unless asked."""
    return [_investor(i) for i in _eco().investors if i.get("serves_founders") or not founders_only]


@router.get("/incubators", response_model=list[IncubatorOut])
async def incubators(
    district: str | None = Query(default=None), sector: str | None = Query(default=None)
) -> list[IncubatorOut]:
    """Sourced incubators, optionally for one district or one sector."""
    if sector and sector not in SECTORS:
        raise HTTPException(status_code=422, detail=f"Unknown sector: {sector}")
    return [
        _incubator(i)
        for i in load_incubators()
        if (not district or i["district"] == district)
        and (not sector or sector in i["sectors"] or "general" in i["sectors"])
    ]


@router.post("/match", response_model=EcosystemMatchOut)
async def match_founder(body: FounderIn) -> EcosystemMatchOut:
    """Investors (ranked, with reasons for the rest), peers and zone companies for a founder."""
    unknown = [s for s in body.sectors if s not in SECTORS]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown sectors: {unknown}")
    r = match(
        _eco(),
        Founder(
            sectors=body.sectors,
            stage=body.stage,
            district=body.district,
            pin=body.pin,
            ask_lakh=body.ask_lakh,
            instrument=body.instrument,
            dpiit=body.dpiit,
            company_age_years=body.company_age_years,
        ),
        limit=body.limit,
    )
    return EcosystemMatchOut(
        zone=(
            FounderZoneOut(
                zone=_zone(r.zone.zone), km=r.zone.km, founder_sector_lq=r.zone.founder_sector_lq
            )
            if r.zone
            else None
        ),
        sector_zones=[SectorZoneOut(zone_id=z.id, name=z.name, lq=v) for z, v in r.sector_zones],
        investors=[
            InvestorMatchOut(
                investor=_investor(m.investor),
                fit=m.fit,
                signals=m.signals,
                reachability=ReachOut(**m.reachability),
                why=m.why,
            )
            for m in r.investors
        ],
        refused=[
            InvestorRefusalOut(investor=_investor(x.investor), reasons=x.reasons) for x in r.refused
        ],
        platforms=[PlatformOut(**{k: p[k] for k in PlatformOut.model_fields}) for p in r.platforms],
        peers=[PeerOut(**{k: p.get(k) for k in PeerOut.model_fields}) for p in r.peers],
        companies=[
            CompanyOut(**{k: c.get(k) for k in CompanyOut.model_fields}) for c in r.companies
        ],
        company_counts=r.company_counts,
        incubators=[
            IncubatorMatchOut(
                incubator=_incubator(m.incubator),
                fit=m.fit,
                signals=m.signals,
                programmes=m.programmes,
                travel=m.travel,
                why=m.why,
                intake=m.intake,
            )
            for m in r.incubators
        ],
        incubators_refused=[
            IncubatorRefusalOut(incubator=_incubator(x.incubator), reasons=x.reasons)
            for x in r.incubators_refused
        ],
        note=_MATCH_NOTE,
    )
