"""Is an investor visibly asking for startups right now? Check its own website.

For every founder-facing investor in the ecosystem index, read the homepage
(robots.txt permitting), follow up to MAX_LINKS links that look like a way in
for founders ("apply", "pitch", "submit your startup", "for founders"), and
record what was found:

  pitch_url   a page where founders can apply or pitch, if any
  open_call   the site uses open-call wording ("applications open", "now
              accepting", "apply now", "cohort", a deadline)
  evidence    the exact phrases, with the URL they were read on
  checked     date of the check

The signal is evidence, not a verdict: no pitch page does not mean an investor
is not investing. It answers "can a founder reach them through their site
today?", and the matcher reports it as such.

Output: backend/app/ecosystem/data/investor_signals.json

Usage:
  python scripts/check_investor_signals.py
"""

from __future__ import annotations

import datetime as dt
import gzip
import html
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "backend/app/ecosystem/data"
UA = "VanigamResearch/0.1 (founder-investor matching; checks public pages only)"
MAX_LINKS = 3
DELAY_S = 1.0

WAY_IN = re.compile(
    r"apply|pitch|submit (?:your )?(?:startup|deck|idea)|founders?\b|get funded|"
    r"raise (?:funding|capital)|funding\b|incubat|accelerat|contact",
    re.I,
)
# Strongest: the link itself says founders can apply or pitch here.
PITCH = re.compile(r"apply|pitch|submit|get funded|funding application|typeform|forms", re.I)
# News and blog posts mention startups and funding constantly; they are not a way in.
NOT_A_WAY_IN = re.compile(r"/(?:news|medias?|blog|press|insights?|articles?|stories)/", re.I)
OPEN_CALL = re.compile(
    r"applications? (?:are )?(?:now )?open|now accepting|accepting applications|apply now|"
    r"apply today|pitch (?:to )?us|submit your (?:pitch|deck|startup)|"
    r"send (?:us )?your (?:pitch|deck)|"
    r"(?:next|upcoming|new) cohort|call for (?:applications|startups)|last date|deadline",
    re.I,
)


def get(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            if "html" not in (r.headers.get("Content-Type") or "html"):
                return None
            body = r.read(5_000_000)
            # Some servers compress whether asked or not; check the bytes, not the header.
            if body[:2] == b"\x1f\x8b":
                body = gzip.decompress(body)
            return body.decode("utf8", "replace")
    except Exception:
        return None
    finally:
        time.sleep(DELAY_S)


def allowed(url: str) -> bool:
    root = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(url))
    rp = urllib.robotparser.RobotFileParser(root + "/robots.txt")
    try:
        rp.read()
    except Exception:
        return True  # no readable robots.txt: public pages are fair to read
    return rp.can_fetch(UA, url)


def visible_text(page: str) -> str:
    page = re.sub(r"<!--.*?-->", " ", page, flags=re.S)
    page = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", page, flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())


def links(base: str, page: str) -> list[tuple[str, str]]:
    host = urllib.parse.urlsplit(base).netloc
    out = []
    pat = r"""<a\b[^>]*href=["']([^"'#]+)["'][^>]*>(.*?)</a>"""
    for href, label in re.findall(pat, page, re.S | re.I):
        url = urllib.parse.urljoin(base, html.unescape(href))
        if urllib.parse.urlsplit(url).netloc.endswith(host.removeprefix("www.")) or any(
            f in url for f in ("forms.gle", "docs.google.com/forms", "typeform.com")
        ):
            out.append((url, " ".join(re.sub(r"<[^>]+>", " ", label).split())))
    return out


def phrases(text: str) -> list[str]:
    found = []
    for m in OPEN_CALL.finditer(text):
        a, b = max(0, m.start() - 60), min(len(text), m.end() + 60)
        found.append(text[a:b].strip())
    return found[:3]


def check(inv: dict) -> dict:
    site = inv.get("website")
    rec = {"checked": dt.date.today().isoformat(), "website": site}
    if not site:
        return {**rec, "status": "no_website"}
    if not allowed(site):
        return {**rec, "status": "robots_disallow"}
    home = get(site)
    if home is None:
        return {**rec, "status": "unreachable"}
    evidence = [{"url": site, "text": t} for t in phrases(visible_text(home))]
    found: dict[str, str] = {}
    for url, label in links(site, home):
        if NOT_A_WAY_IN.search(url) or url.rstrip("/") == site.rstrip("/"):
            continue
        if WAY_IN.search(label) or WAY_IN.search(urllib.parse.urlsplit(url).path):
            found[url] = f"{found.get(url, '')} {label}".strip()  # every label for the URL
    # Pitch-like links first, then the rest (contact, incubation pages).
    candidates = sorted(found, key=lambda u: not (PITCH.search(found[u]) or PITCH.search(u)))
    pitch_url = next((u for u in candidates if PITCH.search(found[u]) or PITCH.search(u)), None)
    for url in candidates[:MAX_LINKS]:
        if not allowed(url):
            continue
        page = get(url)
        if page is None:
            continue
        found = phrases(visible_text(page))
        evidence += [{"url": url, "text": t} for t in found]
        if found and pitch_url is None:
            pitch_url = url
    return {
        **rec,
        "status": "ok",
        "pitch_url": pitch_url,
        "open_call": bool(evidence),
        "evidence": evidence[:4],
    }


def main() -> None:
    eco = json.loads((DATA / "ecosystem_3d.json").read_text(encoding="utf8"))
    out = {}
    for inv in eco["investors"]:
        if not inv.get("serves_founders"):
            continue
        out[inv["slug"]] = check(inv)
        r = out[inv["slug"]]
        route = r.get("pitch_url") or ""
        print(f"{inv['name'][:30]:30} {r['status']:16} open_call={r.get('open_call')} {route}")
    (DATA / "investor_signals.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8"
    )


if __name__ == "__main__":
    main()
