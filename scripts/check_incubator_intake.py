"""Weekly: is each incubator taking applications? Read its own site and record it.

For every incubator with a confirmed website (backend/app/ecosystem/data/
incubators.json), read the homepage (robots.txt permitting) and up to
MAX_LINKS pages that look like intake ("apply", "incubation", "call",
"cohort", "programme", "register"), then classify the visible text with
app.ecosystem.intake.classify_intake: open (with deadline if stated), closed,
apply_page or unknown, keeping the phrases that decided it.

Output: backend/app/ecosystem/data/incubator_intake.json
  {incubator_id: {checked, website, status, deadline, apply_url, evidence}}

Run weekly by .github/workflows/weekly-checks.yml; can be run by hand:
  python scripts/check_incubator_intake.py
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.ecosystem.intake import classify_intake  # noqa: E402
from check_investor_signals import allowed, get, links, visible_text  # noqa: E402

DATA = ROOT / "backend/app/ecosystem/data"
MAX_LINKS = 4
INTAKE_LINK = re.compile(
    r"apply|application|incubat|call for|cohort|programme|program\b|register|admission|join us",
    re.I,
)
APPLY_LINK = re.compile(r"apply|application|register|form", re.I)
NOT_INTAKE = re.compile(
    r"/(?:news|blog|press|media|gallery|events?/\d)|career|recruit|vacanc|advertisement|job",
    re.I,
)


def check(inc: dict, today: dt.date) -> dict:
    site = inc.get("website")
    rec = {"checked": today.isoformat(), "website": site}
    if not site:
        return {**rec, "status": "no_website"}
    if not allowed(site):
        return {**rec, "status": "robots_disallow"}
    home = get(site)
    if home is None:
        return {**rec, "status": "unreachable"}
    pages = [(site, visible_text(home))]
    found: dict[str, str] = {}
    for url, label in links(site, home):
        if (
            NOT_INTAKE.search(url)
            or NOT_INTAKE.search(label)
            or url.rstrip("/") == site.rstrip("/")
        ):
            continue
        if INTAKE_LINK.search(label) or INTAKE_LINK.search(urllib.parse.urlsplit(url).path):
            found[url] = f"{found.get(url, '')} {label}".strip()
    # Apply-like links first.
    ordered = sorted(found, key=lambda u: not (APPLY_LINK.search(found[u]) or APPLY_LINK.search(u)))
    apply_url = next(
        (u for u in ordered if APPLY_LINK.search(found[u]) or APPLY_LINK.search(u)), None
    )
    for url in ordered[:MAX_LINKS]:
        if not allowed(url):
            continue
        page = get(url)
        if page is not None:
            pages.append((url, visible_text(page)))
    return {**rec, **classify_intake(pages, apply_url, today)}


def main() -> None:
    incs = json.loads((DATA / "incubators.json").read_text(encoding="utf8"))["incubators"]
    today = dt.date.today()
    out = {}
    for inc in incs:
        out[inc["id"]] = check(inc, today)
        r = out[inc["id"]]
        due, route = r.get("deadline") or "", r.get("apply_url") or ""
        print(f"{inc['name'][:44]:44} {r['status']:16} {due} {route}")
    (DATA / "incubator_intake.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8"
    )


if __name__ == "__main__":
    main()
