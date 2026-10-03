"""Build the bank-branch index for Vanigam's pilot districts.

Inputs (all public):
  * the RBI-sourced IFSC branch master published by Razorpay
    (https://github.com/razorpay/ifsc/releases), and its bank-name map;
  * OpenStreetMap Nominatim, to locate each pin code (1 request per second,
    per the Nominatim usage policy; results are cached).

Output: backend/app/banking/data/branches_tn5.json — one row per branch with
its pin code, a pin-centroid location, and a bank type, plus the pin centroids
themselves so the API can measure distance from any founder's pin.

Distances computed from this file are pin-centroid approximations (expect
±2–3 km). For production, geocode each branch address once with a paid
provider and replace the pin-centroid coordinates.

Usage:
  python scripts/build_branch_index.py --ifsc IFSC.csv --banknames banknames.json \
      --cache pin_geo_cache.json
"""

from __future__ import annotations

import argparse
import csv
import json
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


def geocode_pin(pin: str) -> list[float] | None:
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"postalcode": pin, "country": "India", "format": "json"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=20))
    except Exception:
        return None
    return [round(float(data[0]["lat"]), 5), round(float(data[0]["lon"]), 5)] if data else None


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ifsc", required=True)
    ap.add_argument("--banknames", required=True)
    ap.add_argument("--cache", default="pin_geo_cache.json")
    ap.add_argument("--district-cache", default="pin_district_cache.json")
    args = ap.parse_args()

    names = json.loads(Path(args.banknames).read_text(encoding="utf8"))
    raw, no_pin = [], 0
    with open(args.ifsc, encoding="utf8") as f:
        for r in csv.DictReader(f):
            if "TAMIL" not in (r["STATE"] or "").upper() or r["IFSC"][:4] in EXCLUDE_CODES:
                continue
            pins = PIN_RE.findall((r["ADDRESS"] or "").replace(" ", ""))
            if not pins:
                no_pin += 1
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
        if not did:
            continue
        code = r["IFSC"][:4]
        rows.append(
            {
                "ifsc": r["IFSC"],
                "bank": NAME_FIX.get(code) or names.get(code) or r["BANK"] or code,
                "bank_code": code,
                "type": BANK_TYPE.get(code, "other"),
                "branch": (r["BRANCH"] or "").strip(),
                "address": " ".join((r["ADDRESS"] or "").split()),
                "district": did,
                "pin": pin,
            }
        )
    dropped = no_pin

    cache_path = Path(args.cache)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    for pin in sorted({r["pin"] for r in rows}):
        if pin in cache:
            continue
        cache[pin] = geocode_pin(pin)
        cache_path.write_text(json.dumps(cache))
        time.sleep(1.1)

    pins = {p: cache[p] for p in sorted({r["pin"] for r in rows}) if cache.get(p)}
    located = [r for r in rows if r["pin"] in pins]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "_meta": {
                    "source": "Razorpay IFSC master (RBI-sourced) + OpenStreetMap Nominatim",
                    "districts": sorted(set(DISTRICTS.values())),
                    "branches": len(located),
                    "district_basis": "India Post district of the branch's pin code",
                    "tn_branches_without_pin_in_address": dropped,
                    "dropped_pin_not_located": len(rows) - len(located),
                    "location_basis": "pin-code centroid (approximate, ±2–3 km)",
                },
                "pins": pins,
                "branches": located,
            },
            ensure_ascii=False,
        ),
        encoding="utf8",
    )
    print(f"{len(located)} branches, {len(pins)} pins located, {dropped} dropped -> {OUT}")


if __name__ == "__main__":
    main()
