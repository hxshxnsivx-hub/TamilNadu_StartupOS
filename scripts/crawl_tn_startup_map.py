"""Crawl the Tamil Nadu Startup Map (tamilnadustartupmap.com) into one JSON file.

The map is a hand-reviewed public directory of Tamil Nadu ventures and
investors, built from the DPIIT recognition register, the MCA company register,
SEBI's register of alternative investment funds and each company's own site.
Every company row carries geocoded coordinates. Its robots.txt allows crawling.

Polite: one request per second, a descriptive User-Agent, and every page cached
on disk so a rerun fetches only what is new. Each detail page is parsed
generically (all <dt>/<dd> pairs, the schema.org Organization block, outbound
website and careers links), so a new field on the site is kept, not lost.

Output (scratch, not committed): tnsm.json —
  {"startups": [...], "investors": [...], "crawled": "<date>"}

Before launch: the directory's terms of reuse must be confirmed with its
maintainers. Vanigam's long-run sources are the same public registers the map
cites.

Usage:
  python scripts/crawl_tn_startup_map.py --cache tnsm_cache --out tnsm.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://tamilnadustartupmap.com"
UA = "VanigamResearch/0.1 (startup ecosystem research; contact via vanigam project)"
DELAY_S = 1.0


def fetch(url: str, cache: Path) -> str:
    path = cache / (hashlib.sha1(url.encode()).hexdigest() + ".html")
    if path.exists():
        return path.read_text(encoding="utf8")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            body = urllib.request.urlopen(req, timeout=60).read().decode("utf8", "replace")
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(10)
    time.sleep(DELAY_S)
    path.write_text(body, encoding="utf8")
    return body


def text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse(url: str, page: str) -> dict:
    body = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    rec: dict = {"source_url": url, "slug": url.rstrip("/").rsplit("/", 1)[-1]}
    for blob in re.findall(r'application/ld\+json">(.*?)</script>', page, flags=re.S):
        try:
            ld = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if ld.get("@type") == "Organization":
            rec["name"] = ld.get("name")
            rec["website"] = ld.get("url")
            rec["description"] = ld.get("description")
            geo = ld.get("geo") or {}
            if "latitude" in geo:
                rec["lat"], rec["lon"] = geo["latitude"], geo["longitude"]
        if ld.get("@type") == "BreadcrumbList":
            crumbs = [i["name"] for i in ld.get("itemListElement", [])]
            rec["breadcrumb"] = crumbs
    if "name" not in rec:
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, flags=re.S)
        rec["name"] = text(h1.group(1)) if h1 else rec["slug"]
        sub = re.search(r"</h1>\s*<p[^>]*>(.*?)</p>", body, flags=re.S)
        rec["description"] = text(sub.group(1)) if sub else None
    fields = {}
    for k, v in re.findall(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", body, flags=re.S):
        fields[text(k)] = text(v)
    rec["fields"] = fields
    links = re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', body, flags=re.S)
    for href, label in links:
        label = text(label).lower()
        if "careers" in label and "careers_url" not in rec:
            rec["careers_url"] = href
        if "visit website" in label and not rec.get("website"):
            rec["website"] = href
    longer = re.search(r'<p class="mt-6[^"]*">(.*?)</p>', body, flags=re.S)
    if longer:
        rec["about"] = text(longer.group(1))
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="tnsm_cache")
    ap.add_argument("--out", default="tnsm.json")
    args = ap.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)

    sitemap = fetch(f"{BASE}/sitemap.xml", cache)
    locs = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    kinds = {"startup": "startups", "investor": "investors"}
    out: dict = {"startups": [], "investors": []}
    todo = [
        (u, kinds[u.split("/")[3]]) for u in locs if u.count("/") == 4 and u.split("/")[3] in kinds
    ]
    for i, (url, kind) in enumerate(todo, 1):
        try:
            out[kind].append(parse(url, fetch(url, cache)))
        except Exception as exc:  # keep going; report at the end
            out.setdefault("errors", []).append({"url": url, "error": str(exc)})
        if i % 50 == 0:
            print(f"{i}/{len(todo)}", flush=True)
    out["crawled"] = dt.date.today().isoformat()
    out["source"] = BASE
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8")
    print(
        f"{len(out['startups'])} startups, {len(out['investors'])} investors, "
        f"{len(out.get('errors', []))} errors -> {args.out}"
    )


if __name__ == "__main__":
    main()
