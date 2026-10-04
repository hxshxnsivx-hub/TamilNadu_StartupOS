"""Precompute road travel times from every pilot pin code to nearby bank branches.

Method
  1. Download each district's drivable road network from OpenStreetMap
     (Overpass API), once, cached to disk.
  2. Build a directed road graph: one edge per road segment, oneway streets
     respected, edge weight = minutes at a free-flow speed for that road type
     (or its posted maxspeed, when lower).
  3. Snap each pin-code centre and each branch to the nearest road node in the
     graph's largest strongly connected component (so every snapped node can
     reach every other), using a k-d tree.
  4. From each pin, run one Dijkstra search (cut off at MAX_MINUTES) over the
     whole graph, then read off the time and road distance to every branch
     within SEARCH_KM in a straight line.

Output: backend/app/banking/data/travel_tn5.json —
  {"pins": {pin: {ifsc: [minutes, road_km]}}}

Times are free-flow estimates: no live traffic, no signals. Real trips at peak
hours take longer; the ranking uses them to compare branches, not to promise an
arrival time.

Usage:
  python scripts/build_travel_times.py --osm-cache-dir osm_roads
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import networkx as nx
from scipy.spatial import cKDTree

DATA = Path(__file__).resolve().parents[1] / "backend/app/banking/data"
BRANCHES = DATA / "branches_tn5.json"
OUT = DATA / "travel_tn5.json"

SEARCH_KM = 15.0  # straight-line radius of branches to time from each pin
MAX_MINUTES = 60.0  # Dijkstra cut-off
TN_LAT = (8.0, 13.6)
TN_LON = (76.0, 80.5)
BUFFER_DEG = 0.12  # ~13 km around a district's points, so border branches are covered
ACCESS_KMH = 15.0  # speed for the short hop between a point and its snapped road node
TILE_DEG = 0.25  # Overpass query tile size (~27 km)

# Free-flow speeds (km/h) by road type: conservative urban values for Tamil Nadu.
SPEED = {
    "motorway": 60,
    "trunk": 45,
    "primary": 35,
    "secondary": 30,
    "tertiary": 25,
    "unclassified": 22,
    "road": 20,
    "residential": 18,
    "living_street": 10,
}
LINK_FACTOR = 0.8  # "_link" ramps run slower than the road they join
ROAD_TYPES = "|".join(
    [*SPEED, "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link"]
)
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
UA = "VanigamResearch/0.1 (pilot travel-time precompute)"


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((la2 - la1) / 2) ** 2
        + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _overpass(bbox: tuple[float, float, float, float]) -> bytes:
    s, w, n, e = bbox
    q = (
        f"[out:json][timeout:600][maxsize:1073741824];"
        f'way["highway"~"^({ROAD_TYPES})$"]({s},{w},{n},{e});'
        f"(._;>;);out body qt;"
    )
    body = urllib.parse.urlencode({"data": q}).encode()
    for attempt in range(6):
        url = OVERPASS[attempt % len(OVERPASS)]
        try:
            req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=900).read()
        except Exception as exc:
            if attempt == 5:
                raise
            print(f"  overpass {url} failed ({exc}); retrying", flush=True)
            time.sleep(30)
    raise RuntimeError("unreachable")


def fetch_roads(bbox: tuple[float, float, float, float], cache: Path) -> dict:
    """Road network for a bounding box, fetched in TILE_DEG tiles (smaller queries
    survive Overpass's load limits) and cached per tile, merged by element id."""
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf8"))
    s, w, n, e = bbox
    rows, cols = math.ceil((n - s) / TILE_DEG), math.ceil((e - w) / TILE_DEG)
    tile_dir = cache.with_suffix("")
    tile_dir.mkdir(parents=True, exist_ok=True)
    elements: dict[tuple[str, int], dict] = {}
    for r in range(rows):
        for c in range(cols):
            tile = (
                s + r * TILE_DEG,
                w + c * TILE_DEG,
                min(n, s + (r + 1) * TILE_DEG),
                min(e, w + (c + 1) * TILE_DEG),
            )
            path = tile_dir / f"{r}_{c}.json"
            if not path.exists():
                path.write_bytes(_overpass(tile))
            for el in json.loads(path.read_text(encoding="utf8"))["elements"]:
                elements[(el["type"], el["id"])] = el
    osm = {"elements": list(elements.values())}
    cache.write_text(json.dumps(osm, separators=(",", ":")), encoding="utf8")
    return osm


def roads_from_pbf(pbf: str, bboxes: dict[str, tuple[float, float, float, float]]) -> dict:
    """One pass over a Geofabrik .osm.pbf extract: drivable ways that touch each
    district's box, in the same element format Overpass returns.

    The fallback when Overpass is overloaded; a local file cannot time out.
    """
    import osmium  # only needed on this path

    keep = re.compile(f"^({ROAD_TYPES})$")
    out = {did: {"nodes": {}, "ways": []} for did in bboxes}
    fp = (
        osmium.FileProcessor(pbf)
        .with_locations("flex_mem")
        .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
        .with_filter(osmium.filter.KeyFilter("highway"))
    )
    for w in fp:
        tags = dict(w.tags)
        if not keep.match(tags.get("highway", "")):
            continue
        try:
            pts = [(n.ref, n.lat, n.lon) for n in w.nodes]
        except osmium.InvalidLocationError:
            continue
        for did, (s, west, n, e) in bboxes.items():
            if any(s <= la <= n and west <= lo <= e for _, la, lo in pts):
                acc = out[did]
                acc["ways"].append(
                    {"type": "way", "id": w.id, "nodes": [p[0] for p in pts], "tags": tags}
                )
                for ref, la, lo in pts:
                    acc["nodes"][ref] = (la, lo)
    return {
        did: {
            "elements": [
                {"type": "node", "id": ref, "lat": la, "lon": lo}
                for ref, (la, lo) in acc["nodes"].items()
            ]
            + acc["ways"]
        }
        for did, acc in out.items()
    }


def speed_of(tags: dict) -> float:
    hw = tags.get("highway", "")
    base = SPEED.get(hw.removesuffix("_link"), 20) * (LINK_FACTOR if hw.endswith("_link") else 1)
    m = re.match(r"\s*(\d+)", tags.get("maxspeed", ""))
    return min(base, float(m.group(1))) if m else base


def build_graph(osm: dict) -> nx.DiGraph:
    coords = {el["id"]: (el["lat"], el["lon"]) for el in osm["elements"] if el["type"] == "node"}
    g = nx.DiGraph()
    for el in osm["elements"]:
        if el["type"] != "way":
            continue
        tags = el.get("tags", {})
        nodes = [n for n in el["nodes"] if n in coords]
        oneway = tags.get("oneway", "no")
        if tags.get("junction") == "roundabout" and oneway == "no":
            oneway = "yes"
        if oneway == "-1":
            nodes.reverse()
        kmh = speed_of(tags)
        for a, b in zip(nodes, nodes[1:], strict=False):
            length = km(coords[a], coords[b])
            minutes = length / kmh * 60
            g.add_edge(a, b, t=minutes, km=length)
            if oneway not in ("yes", "1", "true", "-1"):
                g.add_edge(b, a, t=minutes, km=length)
    for n in g.nodes:
        g.nodes[n]["xy"] = coords[n]
    return g


class Snapper:
    """Nearest road node (in the largest strongly connected component) to a point."""

    def __init__(self, g: nx.DiGraph) -> None:
        core = max(nx.strongly_connected_components(g), key=len)
        self.nodes = list(core)
        lat0 = sum(g.nodes[n]["xy"][0] for n in self.nodes) / len(self.nodes)
        self.kx, self.ky = 111.32 * math.cos(math.radians(lat0)), 110.57
        self.tree = cKDTree([self._xy(g.nodes[n]["xy"]) for n in self.nodes])

    def _xy(self, p: tuple[float, float]) -> tuple[float, float]:
        return (p[1] * self.kx, p[0] * self.ky)

    def snap(self, p: tuple[float, float]) -> tuple[int, float]:
        d, i = self.tree.query(self._xy(p))
        return self.nodes[int(i)], float(d)


def path_km(pred: dict, g: nx.DiGraph, source: int, target: int) -> float:
    total, node = 0.0, target
    while node != source:
        prev = pred[node][0]
        total += g[prev][node]["km"]
        node = prev
    return total


def save(old: dict, out: dict, stats: dict) -> dict:
    """Write after every district, so a later failure keeps finished work."""
    prev = json.loads(OUT.read_text(encoding="utf8"))["_meta"]["stats"] if OUT.exists() else {}
    merged = {**old, **out}
    OUT.write_text(
        json.dumps(
            {
                "_meta": {
                    "method": "Dijkstra over an OpenStreetMap road graph, free-flow speeds",
                    "speeds_kmh": SPEED,
                    "search_km": SEARCH_KM,
                    "max_minutes": MAX_MINUTES,
                    "note": "No live traffic or signals; compare branches, do not promise times.",
                    "stats": {**prev, **stats},
                },
                "pins": merged,
            },
            separators=(",", ":"),
        ),
        encoding="utf8",
    )
    return merged


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm-cache-dir", default="osm_roads")
    ap.add_argument("--districts", nargs="*", help="limit to these district ids")
    ap.add_argument("--pbf", help="Geofabrik .osm.pbf extract to read roads from, not Overpass")
    args = ap.parse_args()
    cache_dir = Path(args.osm_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    idx = json.loads(BRANCHES.read_text(encoding="utf8"))
    pins = {p: (v[0], v[1]) for p, v in idx["pins"].items()}
    branches = idx["branches"]

    def pos(b: dict) -> tuple[float, float] | None:
        if b.get("lat") is not None:
            return (b["lat"], b["lon"])
        return pins.get(b["pin"])

    out: dict[str, dict[str, list[float]]] = {}
    old = json.loads(OUT.read_text(encoding="utf8"))["pins"] if OUT.exists() else {}
    districts = args.districts or sorted({b["district"] for b in branches})
    stats = {}
    merged = old

    def district_pins(did: str) -> list[str]:
        found = sorted({b["pin"] for b in branches if b["district"] == did and b["pin"]})
        return [p for p in found if p in pins]

    bboxes = {}
    for did in districts:
        pts = [pins[p] for p in district_pins(did)] + [
            pos(b) for b in branches if b["district"] == did and pos(b)
        ]
        # One mislocated point would stretch the box across the state (a Chennai pin
        # once geocoded to Gujarat made the box 1,600 km wide), so keep Tamil Nadu only.
        pts = [p for p in pts if TN_LAT[0] <= p[0] <= TN_LAT[1] and TN_LON[0] <= p[1] <= TN_LON[1]]
        bboxes[did] = (
            min(p[0] for p in pts) - BUFFER_DEG,
            min(p[1] for p in pts) - BUFFER_DEG,
            max(p[0] for p in pts) + BUFFER_DEG,
            max(p[1] for p in pts) + BUFFER_DEG,
        )
    missing = {d: b for d, b in bboxes.items() if not (cache_dir / f"{d}.json").exists()}
    if args.pbf and missing:
        t0 = time.time()
        for did, osm in roads_from_pbf(args.pbf, missing).items():
            (cache_dir / f"{did}.json").write_text(json.dumps(osm), encoding="utf8")
        print(f"roads for {sorted(missing)} read from {args.pbf} in {time.time() - t0:.0f}s")

    for did in districts:
        t0 = time.time()
        dist_pins = district_pins(did)
        bbox = bboxes[did]
        osm = fetch_roads(bbox, cache_dir / f"{did}.json")
        g = build_graph(osm)
        snapper = Snapper(g)
        s, w, n, e = bbox
        in_box = [b for b in branches if (q := pos(b)) and s <= q[0] <= n and w <= q[1] <= e]
        snapped = {b["ifsc"]: snapper.snap(pos(b)) for b in in_box}
        pairs = 0
        for pin in dist_pins:
            origin = pins[pin]
            targets = [b for b in in_box if km(origin, pos(b)) <= SEARCH_KM]
            src, src_off = snapper.snap(origin)
            pred, dist = nx.dijkstra_predecessor_and_distance(
                g, src, cutoff=MAX_MINUTES, weight="t"
            )
            row = {}
            for b in targets:
                node, off = snapped[b["ifsc"]]
                if node not in dist:
                    continue
                minutes = dist[node] + (src_off + off) / ACCESS_KMH * 60
                road = path_km(pred, g, src, node) + src_off + off
                row[b["ifsc"]] = [round(minutes, 1), round(road, 2)]
            out[pin] = row
            pairs += len(row)
        stats[did] = {
            "graph_nodes": g.number_of_nodes(),
            "graph_edges": g.number_of_edges(),
            "core_nodes": len(snapper.nodes),
            "pins": len(dist_pins),
            "pin_branch_pairs": pairs,
            "seconds": round(time.time() - t0, 1),
        }
        print(did, stats[did], flush=True)
        merged = save(old, out, stats)

    print(f"{len(merged)} pins -> {OUT}")


if __name__ == "__main__":
    main()
