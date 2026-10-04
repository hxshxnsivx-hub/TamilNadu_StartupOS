"""Research momentum per product domain, from OpenAlex (free, no key).

For each registry domain, count papers per year matching its trend_query and
compare the domain's growth with the growth of ALL research in OpenAlex over
the same complete years. The relative figure is the signal: research volume
rises everywhere every year, so only growth above or below that baseline says
anything about a field.

  rising   domain grows ≥ 3 percentage points a year faster than the baseline
  cooling  ≥ 3 points slower
  flat     in between

This measures research and technology momentum — not market demand, prices or
sales. Market signals (commodity prices, trade data) need other feeds and are
reported as not yet connected.

Output: backend/app/planner/data/registry/signals.json
Usage:   python scripts/build_domain_signals.py
"""

from __future__ import annotations

import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "backend/app/planner/data/registry"
API = "https://api.openalex.org/works"
UA = "VanigamResearch/0.1 (domain research momentum)"
BAND_PP = 3.0


def counts(query: str | None, years: range) -> dict[int, int]:
    params = {"group_by": "publication_year"}
    if query:
        params["search"] = query
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=60))
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)
    time.sleep(0.2)
    got = {int(g["key"]): g["count"] for g in data["group_by"] if str(g["key"]).isdigit()}
    return {y: got.get(y, 0) for y in years}


def cagr(c: dict[int, int]) -> float | None:
    ys = sorted(c)
    first, last = c[ys[0]], c[ys[-1]]
    if first <= 0 or last <= 0:
        return None
    return round(100 * ((last / first) ** (1 / (len(ys) - 1)) - 1), 1)


def main() -> None:
    this_year = dt.date.today().year
    years = range(this_year - 5, this_year)  # five complete years
    doms = json.loads((REGISTRY / "domains.json").read_text(encoding="utf8"))["domains"]
    base = counts(None, years)
    base_cagr = cagr(base)
    out = {}
    for d in doms:
        c = counts(d["trend_query"], years)
        g = cagr(c)
        rel = round(g - base_cagr, 1) if g is not None and base_cagr is not None else None
        label = (
            "unknown"
            if rel is None
            else "rising" if rel >= BAND_PP else "cooling" if rel <= -BAND_PP else "flat"
        )
        out[d["id"]] = {
            "query": d["trend_query"],
            "counts": c,
            "growth_pct": g,
            "vs_all_research_pp": rel,
            "label": label,
        }
        print(f"{d['id']:30} {label:8} {g}% vs {base_cagr}% overall")
    (REGISTRY / "signals.json").write_text(
        json.dumps(
            {
                "checked": dt.date.today().isoformat(),
                "source": "OpenAlex works by publication year",
                "measures": "research and technology momentum, not market demand",
                "years": [years.start, years.stop - 1],
                "baseline": {"counts": base, "growth_pct": base_cagr},
                "not_connected": [
                    "commodity prices (Agmarknet, needs a data.gov.in key)",
                    "trade data",
                    "search interest",
                ],
                "domains": out,
            },
            indent=1,
        ),
        encoding="utf8",
    )


if __name__ == "__main__":
    main()
