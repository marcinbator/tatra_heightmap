#!/usr/bin/env python3
"""
Downloads vector land-cover data for the Tatra Mountains from OSM / Overpass
for bbox: lon 19.55-20.45 E, lat 49.00-49.319372 N.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BBOX = {
    "south": 49.00,
    "west": 19.55,
    "north": 49.319372,
    "east": 20.45,
}

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

QUERIES: dict[str, str] = {
    "forest": r"""
[out:json][timeout:180];
(
  way["natural"="wood"]({s},{w},{n},{e});
  way["landuse"="forest"]({s},{w},{n},{e});
  relation["natural"="wood"]({s},{w},{n},{e});
  relation["landuse"="forest"]({s},{w},{n},{e});
);
out body;
>>;
out skel qt;
""",
    "rocks": r"""
[out:json][timeout:180];
(
  way["natural"="bare_rock"]({s},{w},{n},{e});
  way["natural"="rock"]({s},{w},{n},{e});
  way["natural"="scree"]({s},{w},{n},{e});
  way["natural"="stone"]({s},{w},{n},{e});
  way["natural"="cliff"]({s},{w},{n},{e});
  relation["natural"="bare_rock"]({s},{w},{n},{e});
  relation["natural"="rock"]({s},{w},{n},{e});
  relation["natural"="scree"]({s},{w},{n},{e});
  relation["natural"="cliff"]({s},{w},{n},{e});
);
out body;
>>;
out skel qt;
""",
    "dwarf_pine": r"""
[out:json][timeout:180];
(
  way["natural"="scrub"]({s},{w},{n},{e});
  way["landcover"="scrub"]({s},{w},{n},{e});
  way["natural"="wood"]["species"~"Pinus mugo|kosodrzewina|kosówka",i]({s},{w},{n},{e});
  relation["natural"="scrub"]({s},{w},{n},{e});
);
out body;
>>;
out skel qt;
""",
    "water": r"""
[out:json][timeout:180];
(
  way["natural"="water"]({s},{w},{n},{e});
  way["waterway"="riverbank"]({s},{w},{n},{e});
  way["landuse"="reservoir"]({s},{w},{n},{e});
  way["landuse"="basin"]({s},{w},{n},{e});
  way["water"="lake"]({s},{w},{n},{e});
  way["water"="pond"]({s},{w},{n},{e});
  relation["natural"="water"]({s},{w},{n},{e});
  relation["waterway"="riverbank"]({s},{w},{n},{e});
  relation["landuse"="reservoir"]({s},{w},{n},{e});
);
out body;
>>;
out skel qt;
""",
    "rivers": r"""
[out:json][timeout:180];
(
  way["waterway"="river"]({s},{w},{n},{e});
  way["waterway"="stream"]({s},{w},{n},{e});
  way["waterway"="canal"]({s},{w},{n},{e});
  way["waterway"="drain"]({s},{w},{n},{e});
);
out body;
>>;
out skel qt;
""",
    "roads": r"""
[out:json][timeout:180];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|track|path|footway|cycleway|pedestrian|steps)$"]({s},{w},{n},{e});
);
out body;
>>;
out skel qt;
""",
    "buildings": r"""
[out:json][timeout:180];
(
  way["building"]({s},{w},{n},{e});
  way["landuse"~"^(residential|commercial|industrial|retail|farmyard|construction)$"]({s},{w},{n},{e});
  relation["building"]({s},{w},{n},{e});
  relation["landuse"~"^(residential|commercial|industrial|retail)$"]({s},{w},{n},{e});
);
out body;
>>;
out skel qt;
""",
    "meadows": r"""
[out:json][timeout:180];
(
  way["natural"="grassland"]({s},{w},{n},{e});
  way["natural"="heath"]({s},{w},{n},{e});
  way["natural"="fell"]({s},{w},{n},{e});
  way["natural"="meadow"]({s},{w},{n},{e});
  way["landuse"="meadow"]({s},{w},{n},{e});
  way["landuse"="grass"]({s},{w},{n},{e});
  way["landuse"="farmland"]({s},{w},{n},{e});
  way["landuse"="orchard"]({s},{w},{n},{e});
  relation["natural"="grassland"]({s},{w},{n},{e});
  relation["landuse"="meadow"]({s},{w},{n},{e});
  relation["landuse"="grass"]({s},{w},{n},{e});
  relation["landuse"="farmland"]({s},{w},{n},{e});
);
out body;
>>;
out skel qt;
""",
    "glaciers": r"""
[out:json][timeout:120];
(
  way["natural"="glacier"]({s},{w},{n},{e});
  relation["natural"="glacier"]({s},{w},{n},{e});
);
out body;
>>;
out skel qt;
""",
}


def bbox_tuple() -> tuple[float, float, float, float]:
    return BBOX["south"], BBOX["west"], BBOX["north"], BBOX["east"]


def fill_query(template: str) -> str:
    s, w, n, e = bbox_tuple()
    return template.format(s=s, w=w, n=n, e=e)


def overpass_post(query: str, retries: int = 8) -> dict[str, Any]:
    data = query.encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(retries):
        endpoint = OVERPASS_ENDPOINTS[attempt % len(OVERPASS_ENDPOINTS)]
        req = urllib.request.Request(
            endpoint,
            data=data,
            method="POST",
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "User-Agent": "tatra-terrain-scraper/1.1 (research; local-use)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                raw = resp.read().decode("utf-8")
            return json.loads(raw)
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            last_err = exc
            retry_after = None
            if isinstance(exc, urllib.error.HTTPError):
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
            if retry_after is not None:
                try:
                    wait = float(retry_after)
                except ValueError:
                    wait = 30 * (attempt + 1)
            else:
                wait = min(180, 15 * (attempt + 1))
            wait += random.uniform(0, 5)
            print(
                f"  Overpass error ({endpoint}): {exc}, retrying in {wait:.0f}s",
                file=sys.stderr,
            )
            time.sleep(wait)
    raise RuntimeError(f"Overpass did not respond: {last_err}") from last_err


def assemble_rings(segments: list[list[list[float]]]) -> list[list[list[float]]]:
    """Join way segments of a given role into closed rings by matching shared
    endpoints; a single way rarely closes a large polygon on its own."""
    open_segs = [seg for seg in segments if len(seg) >= 2]
    rings: list[list[list[float]]] = []
    while open_segs:
        ring = open_segs.pop(0)
        changed = True
        while changed and ring[0] != ring[-1]:
            changed = False
            for i, seg in enumerate(open_segs):
                if seg[0] == ring[-1]:
                    ring.extend(seg[1:])
                elif seg[-1] == ring[-1]:
                    ring.extend(list(reversed(seg))[1:])
                elif seg[-1] == ring[0]:
                    ring[0:0] = seg[:-1]
                elif seg[0] == ring[0]:
                    ring[0:0] = list(reversed(seg))[:-1]
                else:
                    continue
                open_segs.pop(i)
                changed = True
                break
        if ring[0] == ring[-1] and len(ring) >= 4:
            rings.append(ring)
    return rings


def point_in_ring(pt: list[float], ring: list[list[float]]) -> bool:
    x, y = pt
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            x_at_y = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_at_y:
                inside = not inside
        j = i
    return inside


def osm_to_geojson(osm: dict[str, Any], layer: str) -> dict[str, Any]:
    nodes: dict[int, tuple[float, float]] = {}
    ways: dict[int, dict[str, Any]] = {}
    features: list[dict[str, Any]] = []

    for el in osm.get("elements", []):
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])
        elif el["type"] == "way":
            ways[el["id"]] = el

    def way_coords(way: dict[str, Any]) -> list[list[float]]:
        coords = []
        for nid in way.get("nodes", []):
            if nid in nodes:
                coords.append([nodes[nid][0], nodes[nid][1]])
        return coords

    for way in ways.values():
        tags = way.get("tags") or {}
        if not tags:
            continue
        coords = way_coords(way)
        if len(coords) < 2:
            continue
        closed = len(coords) >= 4 and coords[0] == coords[-1]
        geom = (
            {"type": "Polygon", "coordinates": [coords]}
            if closed
            else {"type": "LineString", "coordinates": coords}
        )
        features.append(
            {
                "type": "Feature",
                "id": f"way/{way['id']}",
                "properties": {
                    "osm_id": way["id"],
                    "osm_type": "way",
                    "layer": layer,
                    **tags,
                },
                "geometry": geom,
            }
        )

    rel_total = 0
    rel_no_segs = 0
    rel_unclosed = 0
    for el in osm.get("elements", []):
        if el["type"] != "relation":
            continue
        rel_total += 1
        tags = el.get("tags") or {}
        members = el.get("members") or []
        outer_segs: list[list[list[float]]] = []
        inner_segs: list[list[list[float]]] = []
        missing_ways = 0
        for mem in members:
            if mem.get("type") != "way" or mem.get("role") not in (
                "outer",
                "inner",
                "",
            ):
                continue
            way = ways.get(mem.get("ref"))
            if not way:
                missing_ways += 1
                continue
            coords = way_coords(way)
            if len(coords) < 2:
                continue
            (inner_segs if mem.get("role") == "inner" else outer_segs).append(coords)
        if not outer_segs:
            rel_no_segs += 1
            continue
        outer_rings = assemble_rings(outer_segs)
        inner_rings = assemble_rings(inner_segs)
        if not outer_rings:
            rel_unclosed += 1
            continue
        polygons: list[list[list[list[float]]]] = []
        used_inner: set[int] = set()
        for outer in outer_rings:
            holes = []
            for idx, inner in enumerate(inner_rings):
                if idx in used_inner:
                    continue
                if point_in_ring(inner[0], outer):
                    holes.append(inner)
                    used_inner.add(idx)
            polygons.append([outer, *holes])
        geom = (
            {"type": "Polygon", "coordinates": polygons[0]}
            if len(polygons) == 1
            else {"type": "MultiPolygon", "coordinates": polygons}
        )
        features.append(
            {
                "type": "Feature",
                "id": f"relation/{el['id']}",
                "properties": {
                    "osm_id": el["id"],
                    "osm_type": "relation",
                    "layer": layer,
                    **tags,
                },
                "geometry": geom,
            }
        )

    if rel_total:
        print(
            f"  [{layer}] relations: {rel_total}, no segments: {rel_no_segs}, "
            f"unclosed: {rel_unclosed}, OK: {rel_total - rel_no_segs - rel_unclosed}",
            file=sys.stderr,
        )

    return {
        "type": "FeatureCollection",
        "name": layer,
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features,
    }


def scrape_layer(name: str, out_dir: Path) -> Path:
    print(f"Downloading layer: {name} ...")
    osm = overpass_post(fill_query(QUERIES[name]))
    gj = osm_to_geojson(osm, name)
    n = len(gj["features"])
    print(f"  {n} features")
    out = out_dir / f"{name}.geojson"
    out.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
    print(f"  saved {out}")
    return out


def merge_geojsons(paths: list[Path], dest: Path) -> None:
    feats: list[dict[str, Any]] = []
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        feats.extend(data.get("features", []))
    dest.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "name": "tatry_land_cover",
                "bbox": [BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"]],
                "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
                "features": feats,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Merged file: {dest} ({len(feats)} features)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tatra land-cover scraper (OSM / Overpass)")
    p.add_argument("--out", default="land_cover", help="output directory")
    p.add_argument(
        "--layers",
        nargs="+",
        choices=list(QUERIES),
        default=list(QUERIES),
        help="which layers to download",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="re-download even if the layer file already exists",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "bbox": BBOX,
        "source": "OpenStreetMap via Overpass API",
        "data_license": "ODbL 1.0, (c) OpenStreetMap contributors",
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    written: list[Path] = []
    failed: list[str] = []
    for name in args.layers:
        out_path = out_dir / f"{name}.geojson"
        if out_path.exists() and not args.force:
            print(f"Layer {name} already downloaded ({out_path}), skipping.")
            written.append(out_path)
            continue
        try:
            written.append(scrape_layer(name, out_dir))
        except Exception as exc:
            print(f"  Layer {name} failed: {exc}", file=sys.stderr)
            failed.append(name)
        time.sleep(5)

    existing = sorted(out_dir.glob("*.geojson"))
    existing = [p for p in existing if p.name != "all.geojson"]
    if len(existing) > 1:
        merge_geojsons(existing, out_dir / "all.geojson")

    if failed:
        print(
            f"Failed to download: {', '.join(failed)}. Re-run this script to finish "
            f"(already downloaded layers are skipped).",
            file=sys.stderr,
        )
        return 1
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
