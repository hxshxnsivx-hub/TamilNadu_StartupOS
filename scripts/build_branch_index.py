"""Build the bank-branch index for Vanigam's pilot districts.

Inputs (all public):
  * the RBI-sourced IFSC branch master published by Razorpay
    (https://github.com/razorpay/ifsc/releases), and its bank-name map;
  * India Post's All India Pincode Directory with post-office coordinates
    (data.gov.in; mirrored at github.com/dropdevrahul/pincodes-india) — the
    gazetteer used to place branches whose address has no pin code;
  * OpenStreetMap Nominatim, to locate each pin code and any branch the
    gazetteer cannot place (1 request per second, per the Nominatim usage
    policy; results are cached).

Output: backend/app/banking/data/branches_tn5.json — one row per branch with
its pin code, a pin-centroid location, and a bank type, plus the pin centroids
themselves so the API can measure distance from any founder's pin.

Distances computed from this file are pin-centroid approximations (expect
±2–3 km). For production, geocode each branch address once with a paid
provider and replace the pin-centroid coordinates.

Usage:
  python scripts/build_branch_index.py --ifsc IFSC.csv --banknames banknames.json \
      --pincode-dir pincode.csv --cache pin_geo_cache.json
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "backend/app/banking/data/branches_tn5.json"

# The IFSC master's DISTRICT field is free text with many spellings
# ("TRICHY", "TIRUCHIRAPALLY", "COIMBATORE SOUTH", ...), so a branch's district
# is taken from its pin code instead, via India Post's pin directory.
# India Post district name → Vanigam district id.
DISTRICTS = {
    "chennai": "chennai",
    "coimbatore": "coimbatore",
    "tiruppur": "tiruppur",
    "madurai": "madurai",
    "tiruchirappalli": "tiruchirappalli",
}
# Pin prefixes that can fall in these districts; only these pins are looked up.
CANDIDATE_PREFIXES = ("600", "641", "642", "638", "625", "620", "621", "639")

BANK_TYPE = {
    **dict.fromkeys(
        [
            "SBIN",
            "CNRB",
            "IOBA",
            "BARB",
            "IDIB",
            "UBIN",
            "MAHB",
            "BKID",
            "UCBA",
            "PUNB",
            "CBIN",
            "PSIB",
        ],
        "public",
    ),
    **dict.fromkeys(
        ["HDFC", "ICIC", "UTIB", "KKBK", "INDB", "YESB", "IDFB", "RATN", "DCBL", "BDBL"], "private"
    ),
    **dict.fromkeys(["CIUB", "KVBL", "TMBL"], "private_tn"),
    **dict.fromkeys(["FDRL", "SIBL", "CSBK", "DLXB"], "private_kerala"),
    **dict.fromkeys(["IBKL", "KARB", "JAKA"], "private"),
    **dict.fromkeys(
        ["JSFB", "ESFB", "UJVN", "AUBL", "SURY", "UTKS", "ESMF", "UNBA"], "small_finance"
    ),
    **dict.fromkeys(["TNSC", "COSB", "SVCB"], "cooperative"),
    **dict.fromkeys(["FINO", "AIRP", "IPOS", "PYTM", "JIOP"], "payments"),
    **dict.fromkeys(
        [
            "DBSS",
            "CITI",
            "HSBC",
            "SCBL",
            "HVBK",
            "BCEY",
            "BNPA",
            "BOFA",
            "BOTM",
            "DOHB",
            "EBIL",
            "KBKB",
            "SMBC",
            "DEUT",
        ],
        "foreign",
    ),
    "TNGB": "regional_rural",
}
EXCLUDE_CODES = {"RBIS"}  # Reserve Bank of India offices are not lenders
NAME_FIX = {"TNGB": "Tamil Nadu Grama Bank", "DBSS": "DBS Bank India", "CSBK": "CSB Bank"}
PIN_RE = re.compile(r"(?<!\d)(6\d{5})(?!\d)")
UA = "VanigamResearch/0.1 (pilot pin-code bank mapping)"


# Tamil Nadu's bounding box. A pin geocoded outside it is a wrong match (600104,
# Chennai's High Court office, once came back in Gujarat) and is discarded.
TN_LAT = (8.0, 13.6)
TN_LON = (76.0, 80.5)
# Pins OpenStreetMap places wrongly, set by hand from the office's known location.
PIN_OVERRIDES = {"600104": [13.087, 80.287]}  # High Court Building S.O, George Town


def in_tamil_nadu(p: list[float] | tuple[float, float] | None) -> bool:
    return bool(p) and TN_LAT[0] <= p[0] <= TN_LAT[1] and TN_LON[0] <= p[1] <= TN_LON[1]


def geocode_pin(pin: str) -> list[float] | None:
    if pin in PIN_OVERRIDES:
        return PIN_OVERRIDES[pin]
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"postalcode": pin, "country": "India", "format": "json"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=20))
    except Exception:
        return None
    for x in data:
        p = [round(float(x["lat"]), 5), round(float(x["lon"]), 5)]
        if in_tamil_nadu(p):
            return p
    return None


# India Post still files most of Tiruppur district (formed 2009) under
# Coimbatore or Erode. Its taluks, as India Post spells them in the Block
# field, identify the real district.
TIRUPPUR_BLOCKS = {
    "tirupur",
    "tiruppur",
    "avanashi",
    "avinashi",
    "palladam",
    "kangeyam",
    "kangayam",
    "dharapuram",
    "udumalaipettai",
    "udamalpet",
    "madathukulam",
    "uthukuli",
}


def pin_district(pin: str) -> str | None:
    """District for a pin from India Post (majority across its post offices)."""
    url = f"https://api.postalpincode.in/pincode/{pin}"
    try:
        data = json.load(urllib.request.urlopen(urllib.request.Request(url), timeout=20))
        offices = data[0].get("PostOffice") or []
    except Exception:
        return None
    if not offices:
        return None
    blocks = [(o.get("Block") or "").strip().lower() for o in offices]
    if sum(b in TIRUPPUR_BLOCKS for b in blocks) * 2 > len(blocks):
        return "tiruppur"
    names = [(o.get("District") or "").strip().lower() for o in offices]
    return max(set(names), key=names.count)


# --- Recovering branches whose RBI address has no pin code -------------------
# About a quarter of Tamil Nadu branches have no pin in their address. Their
# district is guessed from the free-text DISTRICT/CITY/CENTRE fields, and their
# branch name, which is usually a neighbourhood ("CHENNAI MYLAPORE",
# "COIMBATORE R S PURAM"), is located on OpenStreetMap within that district. A
# match is accepted only if it lands within MAX_KM_FROM_DISTRICT_PIN of a
# located pin code in the same district, so a wrong match cannot move a branch
# across the state. Names that cannot be located are left out rather than
# dropped at the city centre, where their distance would mean nothing.
DISTRICT_TEXT = [
    ("chennai", re.compile(r"CHENN|MADRAS")),
    ("coimbatore", re.compile(r"COIMB|KOVAI|COIMBOT|COIMBUT|COIMBAR")),
    ("tiruppur", re.compile(r"TIRUP+UR\b|TRIPPUR")),
    ("madurai", re.compile(r"\bMADURAI")),
    ("tiruchirappalli", re.compile(r"TRICHY|TIRUCHI?RAP|TRICHIRAP|THIRUCHIRAP|\bTIRUCHI\b")),
]
# Similar-looking places in other districts or states.
DISTRICT_TEXT_EXCLUDE = re.compile(
    r"TIRUCHENG|TIRUCHEND|TRICHUR|TIRUPATH|TIRUPATT|MANAMADURAI|VADAMADURAI|CHENNIMALAI"
)
DISTRICT_LABEL = {
    "chennai": "Chennai",
    "coimbatore": "Coimbatore",
    "tiruppur": "Tiruppur",
    "madurai": "Madurai",
    "tiruchirappalli": "Tiruchirappalli",
}
# Words in branch names that are not a neighbourhood.
NAME_NOISE = re.compile(
    r"\b(CHENNAI|MADRAS|COIMBATORE|KOVAI|TIRUPP?UR|MADURAI|TRICHY|TIRUCHIRAP+ALL?[IY]|"
    r"THIRUCHIRAPALLI|TAMIL ?NADU|TN|BRANCH|MAIN|DIST(RICT)?|CITY|TOWN)\b"
)
# District names glued to a neighbourhood with no space between them.
GLUED_DISTRICT = re.compile(r"(CHENNAI|COIMBATORE|MADURAI|TIRUPP?UR|TRICHY)")
MAX_KM_FROM_DISTRICT_PIN = 12.0


def guess_district(r: dict) -> str | None:
    text = " ".join((r.get(k) or "") for k in ("DISTRICT", "CITY", "CENTRE")).upper()
    if DISTRICT_TEXT_EXCLUDE.search(text):
        return None
    for did, pat in DISTRICT_TEXT:
        if pat.search(text):
            return did
    return None


def locality_query(branch: str) -> str | None:
    name = re.sub(r"[^A-Z ]", " ", branch.upper())
    name = GLUED_DISTRICT.sub(" ", name)  # "AVINASHICOIMBATORE" -> "AVINASHI"
    name = " ".join(NAME_NOISE.sub(" ", name).split())
    # Single letters stay: they are part of names such as "R S Puram", "K K Nagar".
    if not name or all(len(w) == 1 for w in name.split()):
        return None
    return name.title()


# Only settlements count. A road is not a place: "Palladam, Coimbatore" matches
# the Palladam–Kochi highway running through Chettipalayam, 25 km from the town.
PLACE_CLASSES = {"place", "boundary"}

# Other Tamil Nadu districts and towns. A branch whose address names one of
# these is not in the pilot district its free-text field claims (e.g. a
# "Coimbatore" row whose address is in Krishnagiri). Ramanathapuram is left out
# because it is also a Coimbatore neighbourhood.
OTHER_TN_PLACES = re.compile(
    r"\b(ARIYALUR|CHENGALPATTU|CUDDALORE|DHARMAPURI|DINDIGUL|ERODE|KALLAKURICHI|"
    r"KANCHIPURAM|KANCHEEPURAM|KANNIYAKUMARI|NAGERCOIL|KARUR|KRISHNAGIRI|MAYILADUTHURAI|"
    r"NAGAPATTINAM|NAMAKKAL|NILGIRIS|OOTY|PERAMBALUR|PUDUKKOTTAI|SALEM|SIVAGANGA|TENKASI|"
    r"THANJAVUR|THENI|THOOTHUKUDI|TUTICORIN|TIRUNELVELI|TIRUVALLUR|TIRUVANNAMALAI|"
    r"TIRUVARUR|VELLORE|VILUPPURAM|VILLUPURAM|VIRUDHUNAGAR|RANIPET|VEDARANYAM)\b"
)


def geocode_place(q: str) -> list[float] | None:
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "countrycodes": "in", "format": "json", "limit": 5}
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=20))
    except Exception:
        return None
    for x in data:
        if x.get("class") in PLACE_CLASSES:
            return [round(float(x["lat"]), 5), round(float(x["lon"]), 5)]
    return None


def km(a: list[float], b: list[float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((la2 - la1) / 2) ** 2
        + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


# --- Gazetteer: post offices as known places ----------------------------------
# Branch names are usually the name of the local post office ("CHETTIPALAYAM",
# "MALUMICHAMPATTI"). Matching against India Post's directory places a branch
# instantly, with no API call. A match must sit inside the branch's district
# (the perimeter); spelling variants are caught by close matching within that
# district only, so a similar name elsewhere in the state cannot be chosen.
OFFICE_SUFFIX = re.compile(r"\b(B\s?O|S\s?O|H\s?O|P\s?O|EDBO|NDSO)\b")
FUZZY_CUTOFF = 0.88
# Tiruppur was carved out of Coimbatore (and Erode) in 2009; RBI rows still use
# the old district. An exact name match in the sibling district is accepted.
SIBLING_DISTRICTS = {"coimbatore": ("tiruppur",), "tiruppur": ("coimbatore",)}
# Units a founder cannot walk into. They are left out of the index on purpose
# and counted separately, not as "missing".
BACK_OFFICE = re.compile(
    r"\b(SERVICE|ZONAL|REGIONAL|CIRCLE OFFICE|ADMIN|ZAO|CPC|RACPC|RAC|RETAIL HUB|"
    r"RETAIL ASSET|ASSET|HUB|CELL|TREASURY|CURRENCY CHEST|CHEST|STATIONERY|SATTIONERY|"
    r"CLEARING|BACK OFFICE|PROCESSING|CENTRALISED|CENTRALIZED|CONTROLLING|TRAINING|"
    r"SMART|DBU|HEAD OFFICE|LOCAL HEAD|INSPECTION|AUDIT|RECOVERY|SARC|SAMB)\b"
)


def place_key(s: str) -> str:
    """Comparable form of a place name: letters only, no office suffix, no spaces."""
    s = re.sub(r"\(.*?\)", " ", s.upper())  # "T.Nagar (Theni)" -> "T.Nagar"
    s = re.sub(r"[^A-Z ]", " ", s)
    s = OFFICE_SUFFIX.sub(" ", s)
    s = NAME_NOISE.sub(" ", s)  # "Sellur SO Madurai" -> "Sellur"
    return "".join(s.split())


def load_gazetteer(path: str) -> tuple[dict[str, dict[str, str]], dict[str, list[float]]]:
    """Returns (district id → {place key → pin}, pin → fallback coordinates).

    Names and pin codes are the reliable part of this directory. Its
    coordinates are not: of offices whose pin was located independently, 45% sit
    more than 5 km from their pin and 10% more than 38 km. So a matched branch is
    placed at its post office's pin centroid, like every other branch. Only when
    OpenStreetMap cannot locate that pin is the median of the directory's own
    coordinates for the pin used, and then only if it lands inside the district.
    """
    gaz: dict[str, dict[str, str]] = {}
    pts: dict[str, list[tuple[float, float]]] = {}
    with open(path, encoding="utf8", errors="replace") as f:
        for r in csv.DictReader(f):
            did = DISTRICTS.get((r.get("District") or "").strip().lower())
            if not did or "TAMIL" not in (r.get("StateName") or "").upper():
                continue
            key, pin = place_key(r.get("OfficeName") or ""), (r.get("Pincode") or "").strip()
            if not (key and PIN_RE.fullmatch(pin)):
                continue
            gaz.setdefault(did, {}).setdefault(key, pin)
            try:
                lat, lon = float(r["Latitude"]), float(r["Longitude"])
            except (TypeError, ValueError):
                continue
            if 8.0 < lat < 13.6 and 76.0 < lon < 80.5:
                pts.setdefault(pin, []).append((lat, lon))
    fallback = {}
    for pin, ps in pts.items():
        lats, lons = sorted(p[0] for p in ps), sorted(p[1] for p in ps)
        fallback[pin] = [round(lats[len(lats) // 2], 5), round(lons[len(lons) // 2], 5)]
    return gaz, fallback


def gazetteer_lookup(gaz: dict, did: str, name: str) -> tuple[str, str] | None:
    """(pin, district) of the post office matching this name inside the perimeter.

    Perimeter: the branch's district, with close-spelling matches allowed; then
    the sibling district (Coimbatore/Tiruppur), exact names only.
    """
    key = place_key(name)
    if not key:
        return None
    places = gaz.get(did, {})
    if key in places:
        return places[key], did
    close = difflib.get_close_matches(key, places.keys(), n=1, cutoff=FUZZY_CUTOFF)
    if close:
        return places[close[0]], did
    for sib in SIBLING_DISTRICTS.get(did, ()):
        if key in gaz.get(sib, {}):
            return gaz[sib][key], sib
    return None


def make_row(r: dict, names: dict, did: str, pin: str) -> dict:
    code = r["IFSC"][:4]
    return {
        "ifsc": r["IFSC"],
        "bank": NAME_FIX.get(code) or names.get(code) or r["BANK"] or code,
        "bank_code": code,
        "type": BANK_TYPE.get(code, "other"),
        "branch": (r["BRANCH"] or "").strip(),
        "address": " ".join((r["ADDRESS"] or "").split()),
        "district": did,
        "pin": pin,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ifsc", required=True)
    ap.add_argument("--banknames", required=True)
    ap.add_argument("--cache", default="pin_geo_cache.json")
    ap.add_argument("--district-cache", default="pin_district_cache.json")
    ap.add_argument("--locality-cache", default="locality_places_cache.json")
    ap.add_argument("--pincode-dir", help="India Post All India Pincode Directory CSV")
    ap.add_argument(
        "--no-osm-fallback",
        action="store_true",
        help="place no-pin branches by gazetteer only (no Nominatim calls)",
    )
    ap.add_argument(
        "--osm-cache-only",
        action="store_true",
        help="use earlier Nominatim results from the cache but make no new requests",
    )
    args = ap.parse_args()
    gaz, gaz_coords = load_gazetteer(args.pincode_dir) if args.pincode_dir else ({}, {})

    names = json.loads(Path(args.banknames).read_text(encoding="utf8"))
    raw, nopin_rows, no_pin = [], [], 0
    with open(args.ifsc, encoding="utf8") as f:
        for r in csv.DictReader(f):
            if "TAMIL" not in (r["STATE"] or "").upper() or r["IFSC"][:4] in EXCLUDE_CODES:
                continue
            pins = PIN_RE.findall((r["ADDRESS"] or "").replace(" ", ""))
            if not pins:
                no_pin += 1
                did = guess_district(r)
                if did:
                    nopin_rows.append((r, did))
                continue
            if pins[-1].startswith(CANDIDATE_PREFIXES):
                raw.append((r, pins[-1]))

    dcache_path = Path(args.district_cache)
    dcache = json.loads(dcache_path.read_text()) if dcache_path.exists() else {}
    for pin in sorted({p for _, p in raw}):
        if pin not in dcache:
            dcache[pin] = pin_district(pin)
            dcache_path.write_text(json.dumps(dcache))
            time.sleep(0.3)

    rows = []
    for r, pin in raw:
        did = DISTRICTS.get(dcache.get(pin) or "")
        if did:
            rows.append(make_row(r, names, did, pin))

    cache_path = Path(args.cache)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    # Older runs cached results without the Tamil Nadu check: correct them first.
    cache.update(PIN_OVERRIDES)
    for p, v in list(cache.items()):
        if v is not None and not in_tamil_nadu(v):
            del cache[p]  # looked up again below
    for pin in sorted({r["pin"] for r in rows}):
        if pin in cache:
            continue
        cache[pin] = geocode_pin(pin)
        cache_path.write_text(json.dumps(cache))
        time.sleep(1.1)

    pins = {p: cache[p] for p in sorted({r["pin"] for r in rows}) if cache.get(p)}
    located = [r for r in rows if r["pin"] in pins]
    seen = {r["ifsc"] for r in located}

    # Recover branches with no pin in their address, by neighbourhood.
    # The district is then taken from the nearest located pin, not from the
    # free-text field, which still uses pre-2009 boundaries in places.
    pin_district_of = {r["pin"]: r["district"] for r in located}
    lcache_path = Path(args.locality_cache)
    lcache = json.loads(lcache_path.read_text()) if lcache_path.exists() else {}

    def lookup(q: str) -> list[float] | None:
        if q not in lcache:
            if args.osm_cache_only:
                return None
            lcache[q] = geocode_place(q)
            lcache_path.write_text(json.dumps(lcache))
            time.sleep(1.1)
        return lcache[q]

    def nearest_district(loc: list[float]) -> str | None:
        p, dist = min(((p, km(loc, c)) for p, c in pins.items()), key=lambda t: t[1])
        return pin_district_of[p] if dist <= MAX_KM_FROM_DISTRICT_PIN else None

    recovered, unrecovered, back_office = 0, 0, 0
    by_method = {"gazetteer": 0, "osm": 0}
    for r, did in nopin_rows:
        if r["IFSC"] in seen:
            continue
        if BACK_OFFICE.search((r["BRANCH"] or "").upper()):
            back_office += 1
            continue
        name = locality_query(r["BRANCH"] or "")
        if not name or OTHER_TN_PLACES.search((r["ADDRESS"] or "").upper()):
            unrecovered += 1
            continue
        # 1. Gazetteer: a post office of that name inside the perimeter gives the
        #    branch a pin code (instant; the pin is located once and cached).
        hit = gazetteer_lookup(gaz, did, name)
        if hit:
            office_pin, office_district = hit
            if office_pin not in cache:
                cache[office_pin] = geocode_pin(office_pin)
                cache_path.write_text(json.dumps(cache))
                time.sleep(1.1)
            where = cache.get(office_pin)
            if not where and office_pin in gaz_coords:
                # OpenStreetMap has no location for this pin: use the directory's
                # own median, but only if it lands inside the same district.
                cand = gaz_coords[office_pin]
                if nearest_district(cand) == office_district:
                    where = cand
            if where:
                pins.setdefault(office_pin, where)
                pin_district_of.setdefault(office_pin, office_district)
                row = make_row(r, names, office_district, office_pin)
                row["located_by"] = "post_office"
                located.append(row)
                seen.add(r["IFSC"])
                recovered += 1
                by_method["gazetteer"] += 1
                continue
        # 2. Only what the gazetteer cannot place goes to OpenStreetMap.
        district, loc = None, None
        if not args.no_osm_fallback:
            loc = lookup(f"{name}, {DISTRICT_LABEL[did]}, Tamil Nadu") or lookup(
                f"{name}, Tamil Nadu"
            )
            district = nearest_district(loc) if loc else None
        if not district:
            unrecovered += 1
            continue
        row = make_row(r, names, district, "")
        row.update(lat=loc[0], lon=loc[1], located_by="locality")
        by_method["osm"] += 1
        located.append(row)
        seen.add(r["IFSC"])
        recovered += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "_meta": {
                    "source": (
                        "Razorpay IFSC master (RBI-sourced), India Post pincode directory, "
                        "OpenStreetMap"
                    ),
                    "districts": sorted(set(DISTRICTS.values())),
                    "branches": len(located),
                    "located_by_address_pin": len(located) - recovered,
                    "recovered_without_address_pin": recovered,
                    "locality_method_counts": by_method,
                    "district_basis": "India Post district of the pin; district text when no pin",
                    "tn_branches_without_pin_in_address": no_pin,
                    "no_pin_in_pilot_districts_unrecovered": unrecovered,
                    "back_office_units_excluded": back_office,
                    "dropped_pin_not_located": len(rows) - (len(located) - recovered),
                    "location_basis": "pin-code or neighbourhood centroid (approximate, ±2–3 km)",
                },
                "pins": pins,
                "branches": located,
            },
            ensure_ascii=False,
        ),
        encoding="utf8",
    )
    print(
        f"{len(located)} branches ({recovered} recovered without an address pin {by_method}, "
        f"{unrecovered} not, {back_office} back-office units excluded), "
        f"{len(pins)} pins -> {OUT}"
    )


if __name__ == "__main__":
    main()
