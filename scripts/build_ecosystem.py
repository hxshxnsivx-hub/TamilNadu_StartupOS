"""Build the startup-ecosystem index for the pilot districts (Chennai, Coimbatore, Madurai).

Three layers, each placed on a pin code so the backend can cut districts into
hotspot zones:

  companies  MCA company master data (data.gov.in), active companies only.
             Sector from the NIC industry code. The register's addresses are
             cut at ~70 characters and rarely carry a district, so a company is
             placed by, in order: a pin code in the address; a Chennai postal
             zone ("CHENNAI-18" -> 600018); or a locality that matches exactly
             one post office in the India Post directory, among the districts
             under the company's Registrar of Companies. A name found in more
             than one district is left unplaced rather than guessed.
  startups   Tamil Nadu Startup Map (hand-reviewed; geocoded street addresses).
  investors  Same directory's investor layer (SEBI AIF register based).

Output: backend/app/ecosystem/data/ecosystem_3d.json

Usage (from the scratch folder holding the inputs):
  python scripts/build_ecosystem.py --mca mca_tn.csv --pincode-dir pincode.csv \
      --pin-geo pin_geo_cache.json --pin-district pin_district_cache.json --tnsm tnsm.json
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ecosystem.taxonomy import AGNOSTIC, sector_of_nic, sectors_in  # noqa: E402

OUT = ROOT / "backend/app/ecosystem/data/ecosystem_3d.json"
BRANCHES = ROOT / "backend/app/banking/data/branches_tn5.json"
PILOT = ("chennai", "coimbatore", "madurai")
PIN_RE = re.compile(r"(?<!\d)(6\d{2})\s?(\d{3})(?!\d)")
CHENNAI_ZONE = re.compile(r"(?:CHENNAI|MADRAS)\s*[-:.,]?\s*(\d{1,3})\b")
# Districts under the Registrar of Companies, Coimbatore; every other Tamil
# Nadu district files with ROC Chennai.
ROC_COIMBATORE = {
    "coimbatore", "tiruppur", "erode", "salem", "namakkal", "nilgiris", "the nilgiris",
    "karur", "dharmapuri", "krishnagiri", "dindigul",
}  # fmt: skip
OFFICE_SUFFIX = re.compile(r"\b(B\s?O|S\s?O|H\s?O|P\s?O|EDBO|NDSO|GPO)\b")
GENERIC_KEYS = {"MAIN", "ROAD", "STREET", "NAGAR", "COLONY", "EXTENSION", "TAMILNADU", "INDIA"}
STARTUP_CITY = {"chennai": "chennai", "coimbatore": "coimbatore", "madurai": "madurai"}
MAX_KM_TO_PIN = 6.0  # a startup is assigned the nearest located pin within this distance
# A city named in the address limits matches to that city's districts.
ADDRESS_CITY = [
    (re.compile(r"CHENNAI|MADRAS"), {"chennai"}),
    (re.compile(r"COIMBATORE|KOVAI"), {"coimbatore", "tiruppur"}),
    (re.compile(r"\bMADURAI\b"), {"madurai"}),
]


def metro_district(pin: str, pin_district: dict) -> str:
    """District of a pin; every 600xxx pin is Chennai metro, whatever India Post files it under
    (Ambattur and Valasaravakkam sit in Tiruvallur district, Sholinganallur's neighbours in
    Chengalpattu)."""
    return "chennai" if pin.startswith("600") else pin_district.get(pin, "")


def place_key(s: str) -> str:
    s = re.sub(r"\(.*?\)", " ", s.upper())
    s = re.sub(r"[^A-Z ]", " ", s)
    s = OFFICE_SUFFIX.sub(" ", s)
    return "".join(s.split())


def km(a, b) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((la2 - la1) / 2) ** 2
        + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def load_post_offices(path: str):
    """place key -> {(district, pin)}, pin -> district (majority), pin -> office names."""
    gaz: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    votes: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    names: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)
    rank = {"HO": 0, "H.O": 0, "SO": 1, "S.O": 1, "PO": 1}
    with open(path, encoding="utf8", errors="replace") as f:
        for r in csv.DictReader(f):
            if "TAMIL" not in (r.get("StateName") or "").upper():
                continue
            did = (r.get("District") or "").strip().lower()
            pin = (r.get("Pincode") or "").strip()
            key = place_key(r.get("OfficeName") or "")
            if not (did and key and len(pin) == 6):
                continue
            gaz[key].add((did, pin))
            votes[pin][did] += 1
            office = re.sub(r"\(.*?\)", "", r.get("OfficeName") or "")
            office = re.sub(r"\b(?:[BSHP]\.?\s?O|G\.?P\.?O|EDBO|NDSO)\b\.?", "", office)
            office = " ".join(office.split()).strip(" .").title()
            names[pin].append((rank.get((r.get("OfficeType") or "").upper(), 2), office))
    pin_district = {p: v.most_common(1)[0][0] for p, v in votes.items()}
    # A pin is named after its head or sub post office, not a village branch office.
    return gaz, pin_district, {p: [min(v)[1]] for p, v in names.items()}


def candidates(address: str) -> list[str]:
    """Place keys to try, most specific (end of the address) first."""
    parts = [p for p in re.split(r"[,;]", address.upper()) if p.strip()]
    keys: list[str] = []
    for part in reversed(parts[-4:]):
        words = re.sub(r"[^A-Z ]", " ", part).split()
        keys.append(place_key(part))
        for n in (3, 2, 1):  # trailing words: "...2ND STREETINJAMBAKKAM" -> "STREETINJAMBAKKAM"
            if len(words) >= n:
                keys.append(place_key(" ".join(words[-n:])))
    seen, out = set(), []
    for k in keys:
        if len(k) >= 5 and k not in GENERIC_KEYS and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def locate_company(r: dict, gaz, pin_district) -> tuple[str, str, str] | None:
    """(pin, district, located_by) for an active company, or None."""
    a = r["REGISTERED_OFFICE_ADDRESS"].upper()
    m = PIN_RE.search(a)
    if m:
        pin = m.group(1) + m.group(2)
        return (pin, metro_district(pin, pin_district), "address_pin")
    m = CHENNAI_ZONE.search(a)
    if m and 1 <= int(m.group(1)) <= 130:
        pin = f"600{int(m.group(1)):03d}"
        if pin in pin_district:
            return (pin, "chennai", "postal_zone")
    coimbatore_roc = "COIMBATORE" in r["REGISTRAR_OF_COMPANIES"].upper()
    named = set().union(*(ds for pat, ds in ADDRESS_CITY if pat.search(a)))
    for key in candidates(a):
        hits = {
            (metro_district(p, pin_district), p)
            for d, p in gaz.get(key, ())
            if (d in ROC_COIMBATORE) == coimbatore_roc
        }
        if named:
            hits = {(d, p) for d, p in hits if d in named}
        districts = {d for d, _ in hits}
        if len(districts) == 1:
            pins = sorted(p for _, p in hits)
            return (pins[0], districts.pop(), "post_office")
        if len(districts) > 1:
            return None  # ambiguous name: do not guess
    return None


def build_companies(path: str, gaz, pin_district, pins) -> tuple[list[dict], dict]:
    out, stats = [], collections.Counter()
    with open(path, encoding="latin-1") as f:
        for r in csv.DictReader(f):
            if r["COMPANY_STATUS"] != "ACTV":
                continue
            stats["active"] += 1
            loc = locate_company(r, gaz, pin_district)
            if not loc:
                stats["unplaced"] += 1
                continue
            pin, did, how = loc
            stats[f"placed_{how}"] += 1
            if did not in PILOT:
                continue
            if pin not in pins:
                stats["pilot_pin_not_located"] += 1
                continue
            year = r["DATE_OF_REGISTRATION"][-4:]

            def money(v: str) -> float:
                try:
                    return float(v)
                except ValueError:
                    return 0.0

            out.append(
                {
                    "cin": r["CORPORATE_IDENTIFICATION_NUMBER"],
                    "name": " ".join(r["COMPANY_NAME"].split()).title(),
                    "class": r["COMPANY_CLASS"],
                    "nic": r["INDUSTRIAL_CLASS"],
                    "sector": sector_of_nic(r["INDUSTRIAL_CLASS"]),
                    "year": int(year) if year.isdigit() else None,
                    "paidup_lakh": round(money(r["PAIDUP_CAPITAL"]) / 1e5, 2),
                    "pin": pin,
                    "district": did,
                    "located_by": how,
                }
            )
            stats[f"pilot_{did}"] += 1
    return out, dict(stats)


def build_startups(tnsm: dict, pins: dict, pin_district) -> tuple[list[dict], dict]:
    out, stats = [], collections.Counter()
    pilot_pins = {p: xy for p, xy in pins.items() if metro_district(p, pin_district) in PILOT}
    for s in tnsm["startups"]:
        f = s.get("fields", {})
        city = (f.get("City") or "").strip().lower()
        did = STARTUP_CITY.get(city)
        stats["total"] += 1
        if not did:
            stats["outside_pilot"] += 1
            continue
        # Place by the pin in the street address first; most pages carry no map
        # coordinates. Then by coordinates; else keep the startup at district level.
        m = PIN_RE.search(f.get("Location") or "")
        pin = m.group(1) + m.group(2) if m else ""
        if pin and pin in pilot_pins:
            here = pilot_pins[pin]
            stats["placed_by_address_pin"] += 1
        elif s.get("lat") is not None:
            here = (s["lat"], s["lon"])
            near = min(pilot_pins.items(), key=lambda kv: km(here, kv[1]), default=None)
            pin = near[0] if near and km(here, near[1]) <= MAX_KM_TO_PIN else ""
            stats["placed_by_coordinates"] += 1
        else:
            here, pin = None, ""
            stats["district_only"] += 1
        label = f.get("Sector") or ""
        out.append(
            {
                "slug": s["slug"],
                "name": s.get("name"),
                "website": s.get("website"),
                "careers_url": s.get("careers_url"),
                "description": s.get("description"),
                "sector_label": label,
                "sectors": sectors_in(label) or sectors_in(s.get("description") or ""),
                "stage": f.get("Funding stage") or f.get("Stage"),
                "tier": f.get("Ecosystem tier"),
                "status": f.get("Status"),
                # Scaling signals as the directory states them; blank when not published.
                "founded": f.get("Founded"),
                "team_size": f.get("Team size"),
                "total_funding": f.get("Total funding"),
                "latest_round": f.get("Latest round"),
                "company_type": f.get("Company type"),
                "area": f.get("Area"),
                "district": did,
                "lat": here[0] if here else None,
                "lon": here[1] if here else None,
                "pin": pin,
                "source_url": s["source_url"],
            }
        )
        stats[f"pilot_{did}"] += 1
    return out, dict(stats)


# "Invests in" on the directory -> (asset class, serves founders?, instrument)
ASSET_CLASS = [
    ("incubator", True, "equity"),
    ("venture", True, "equity"),
    ("angel", True, "equity"),
    ("mixed", True, "both"),
    ("growth", True, "equity"),
    ("climate", True, "equity"),
    ("private credit", True, "debt"),
    ("real estate", False, None),
    ("public markets", False, None),
    ("infrastructure", False, None),
]
NOT_FOR_FOUNDERS = {
    "real estate": "Real-estate fund: does not invest in startups",
    "public markets": "Invests in listed shares, not private startups",
    "infrastructure": "Infrastructure fund: does not invest in startups",
}
STAGE_WORDS = [
    ("pre_seed", re.compile(r"pre-?seed|incubat", re.I)),
    ("seed", re.compile(r"\bseed\b|angel", re.I)),
    ("pre_series_a", re.compile(r"pre-?series a", re.I)),
    ("early", re.compile(r"early[- ]stage", re.I)),
    ("series_a", re.compile(r"(?<!pre-)(?<!pre )series a\b", re.I)),
    ("growth", re.compile(r"growth|late[- ]stage|mid-?market|buyout", re.I)),
]
# A venture fund that names no stage is an early-stage fund.
DEFAULT_STAGES = {
    "angel": ["pre_seed", "seed"],
    "incubator": ["pre_seed", "seed"],
    "venture": ["seed", "early"],
}
# Cheque sizes only where the text says what the investor writes, not
# revenue bands or fund sizes: "writing INR 1-3 Cr", "cheques of around $1M".
TICKET_INR = re.compile(
    r"(?:writ\w*|cheques?(?: of)?)\s+(?:around\s+)?INR\s*([\d.]+)\s*(?:-|to|–)\s*([\d.]+)\s*Cr",
    re.I,
)
TICKET_USD = re.compile(r"cheques? of (?:around|about|~)\s*\$\s*([\d.]+)\s*M", re.I)
USD_INR = 85.0
# Text that names portfolio companies or negates a stage is not thesis.
PORTFOLIO = re.compile(r"(?:portfolio includes|including)\b[^.]*\.?", re.I)
NEGATED = re.compile(r"\bnot\s+(?:a\s+)?[\w-]+(?:\s+[\w-]+)?", re.I)
SAYS_NOT_FOUNDERS = re.compile(r"not founders|not for founders", re.I)


def classify_investor(fields: dict, text: str) -> dict:
    kind = (fields.get("Invests in") or "").split("·")[0].strip().lower()
    asset, founders, instrument = "other", False, None
    for name, f, ins in ASSET_CLASS:
        if kind.startswith(name):
            asset, founders, instrument = name.replace(" ", "_"), f, ins
            break
    reason = None
    if founders and SAYS_NOT_FOUNDERS.search(text) and asset != "private_credit":
        founders, reason = False, "Says it serves family offices or listed markets, not founders"
    thesis = NEGATED.sub(" ", PORTFOLIO.sub(" ", text))
    stages = [s for s, pat in STAGE_WORDS if pat.search(thesis)]
    if not stages:
        stages = DEFAULT_STAGES.get(asset, [])
    ticket = None
    m = TICKET_INR.search(text)
    if m:
        ticket = [float(m.group(1)) * 100, float(m.group(2)) * 100]  # lakh
    else:
        m = TICKET_USD.search(text)
        if m:
            v = round(float(m.group(1)) * USD_INR * 10, 1)  # $M -> lakh
            ticket = [v, v]
    sectors = [] if asset == "real_estate" else sectors_in(thesis)
    return {
        "asset_class": asset,
        "serves_founders": founders,
        "not_for_founders_reason": (
            None if founders else (reason or NOT_FOR_FOUNDERS.get(kind) or "Not a startup investor")
        ),
        "instrument": instrument,
        "stages": stages,
        "sectors": sectors,
        "generalist": founders and (not sectors or bool(AGNOSTIC.search(thesis))),
        "ticket_lakh": ticket,
    }


def build_investors(tnsm: dict) -> list[dict]:
    out = []
    for i in tnsm["investors"]:
        f = i.get("fields", {})
        # Sector words come from the tags and the thesis, not from portfolio names.
        thesis = " ".join(x for x in (i.get("description"), i.get("about"), f.get("Tags")) if x)
        cls = classify_investor(f, thesis)
        out.append(
            {
                "slug": i["slug"],
                "name": i.get("name"),
                "website": i.get("website"),
                "summary": i.get("description"),
                "about": i.get("about"),
                "invests_in": f.get("Invests in"),
                "tags": [t.strip() for t in (f.get("Tags") or "").split(",") if t.strip()],
                "city": f.get("City"),
                "operates_from": f.get("Operates from"),
                "fund_size": f.get("Fund size"),
                **cls,
                "source_url": i["source_url"],
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mca", required=True)
    ap.add_argument("--pincode-dir", required=True)
    ap.add_argument("--pin-geo", required=True)
    ap.add_argument("--pin-district", required=True)
    ap.add_argument("--tnsm", required=True)
    args = ap.parse_args()

    gaz, po_district, office_names = load_post_offices(args.pincode_dir)
    # India Post API district (with the Tiruppur fix) wins over the directory majority.
    api_district = json.loads(Path(args.pin_district).read_text(encoding="utf8"))
    pin_district = {**po_district, **{p: d for p, d in api_district.items() if d}}
    pins = {p: tuple(v) for p, v in json.loads(BRANCHES.read_text(encoding="utf8"))["pins"].items()}
    for p, v in json.loads(Path(args.pin_geo).read_text(encoding="utf8")).items():
        if v and p not in pins:
            pins[p] = tuple(v)

    companies, cstats = build_companies(args.mca, gaz, pin_district, pins)
    tnsm = json.loads(Path(args.tnsm).read_text(encoding="utf8"))
    startups, sstats = build_startups(tnsm, pins, pin_district)
    investors = build_investors(tnsm)

    used = {c["pin"] for c in companies} | {s["pin"] for s in startups if s["pin"]}
    used |= {p for p in pins if metro_district(p, pin_district) in PILOT}
    pin_rows = {
        p: {
            "lat": pins[p][0],
            "lon": pins[p][1],
            "district": metro_district(p, pin_district),
            "name": office_names.get(p, [""])[0],
        }
        for p in sorted(used)
        if p in pins and metro_district(p, pin_district) in PILOT
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "_meta": {
                    "districts": list(PILOT),
                    "sources": {
                        "companies": "MCA company master data, Tamil Nadu (data.gov.in, 2020)",
                        "startups": f"{tnsm['source']} (crawled {tnsm['crawled']})",
                        "investors": f"{tnsm['source']} investor layer",
                        "pins": "India Post directory; pin centres from OpenStreetMap",
                        "chennai": "Chennai metro: every 600xxx pin, across district lines",
                    },
                    "company_stats": cstats,
                    "startup_stats": sstats,
                    "investors": len(investors),
                    "caveats": [
                        "Company register snapshot ends early 2020: newer companies are absent.",
                        "Companies are placed at their registered office, not where they operate.",
                    ],
                },
                "pins": pin_rows,
                "companies": companies,
                "startups": startups,
                "investors": investors,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf8",
    )
    print(json.dumps({"companies": cstats, "startups": sstats, "investors": len(investors)}))
    print(f"{len(pin_rows)} pins -> {OUT}")


if __name__ == "__main__":
    main()
