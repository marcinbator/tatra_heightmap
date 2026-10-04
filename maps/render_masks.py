#!/usr/bin/env python3
"""
Generuje binarne maski (czarno-białe) per warstwa, dopasowane piksel-w-piksel
do heightmapy, do użycia z WorldPainter: Edit -> Import -> Mask as terrain or layer.

Drogi klasyfikowane dodatkowo po tagu `surface` (nie tylko `highway`), zeby
asfaltowe drogi oznaczone jako track/path (np. Palenica -> Morskie Oko)
trafily do roads_paved, nie roads_path.

    uv run --with matplotlib --with shapely --with pyproj --with pillow render_masks.py \
        --in land_cover --out masks \
        --origin-x 541503.463 --origin-y 161486.572 \
        --width-px 11007 --height-px 5119 --pixel-size 5
"""

from __future__ import annotations
import argparse, json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform as shp_transform
from PIL import Image

TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True)

PAVED_HIGHWAY = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential",
    "living_street",
    "service",
}
PAVED_SURFACE = {"asphalt", "paved", "concrete", "paving_stones", "sett", "cobblestone"}

# nazwa_pliku -> (kind, linewidth)  -- linewidth tylko dla "line"
LAYERS = {
    "forest": ("fill", None),
    "dwarf_pine": ("fill", None),
    "rocks": ("fill", None),
    "water": ("fill", None),
    "glaciers": ("fill", None),
    "buildings": ("fill", None),
    "meadows": ("fill", None),
    "rivers": ("line", 1.0),
    "roads_paved": ("line", 1.8),
    "roads_path": ("line", 0.5),
    "roads_steps": ("line", 0.8),
}


def is_paved(tags: dict) -> bool:
    surface = tags.get("surface")
    if surface in PAVED_SURFACE:
        return True
    if surface is not None:
        # surface jawnie podany i nie jest utwardzony (gravel, dirt, ground, grass...)
        return False
    # brak tagu surface -> zgaduj po typie drogi
    return tags.get("highway") in PAVED_HIGHWAY


def to_2180(geom):
    return shp_transform(TRANSFORMER.transform, geom)


def polygon_path(geom):
    verts, codes = [], []

    def add_ring(xy):
        pts = list(zip(*xy))
        if len(pts) < 3:
            return
        verts.extend(pts)
        codes.append(MplPath.MOVETO)
        codes.extend([MplPath.LINETO] * (len(pts) - 2))
        codes.append(MplPath.CLOSEPOLY)

    if geom.geom_type == "Polygon":
        add_ring(geom.exterior.xy)
        for ring in geom.interiors:
            add_ring(ring.xy)
        return MplPath(verts, codes) if verts else None
    return None


def collect(features, clip):
    patches, lines = [], []
    for feat in features:
        raw = feat.get("geometry")
        if not raw:
            continue
        try:
            geom = shape(raw)
            if not geom.is_valid:
                geom = geom.buffer(0)
            geom = to_2180(geom).intersection(clip)
            if geom.is_empty:
                continue
            geoms = list(geom.geoms) if geom.geom_type.startswith("Multi") else [geom]
            for g in geoms:
                if g.geom_type == "Polygon":
                    p = polygon_path(g)
                    if p is not None:
                        patches.append(PathPatch(p))
                elif g.geom_type in ("LineString", "LinearRing"):
                    lines.append(list(g.coords))
        except Exception:
            pass
    return patches, lines


def render(
    name,
    patches,
    lines,
    kind,
    lw,
    out_dir,
    xmin,
    xmax,
    ymin,
    ymax,
    width_px,
    height_px,
    dpi,
):
    fig_w = width_px / dpi
    fig_h = height_px / dpi
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")

    if kind == "fill" and patches:
        ax.add_collection(PatchCollection(patches, facecolor="white", edgecolor="none"))
    if kind == "line" and lines:
        ax.add_collection(LineCollection(lines, colors="white", linewidths=lw or 1.0))

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect(1)
    ax.axis("off")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    out_path = out_dir / f"mask_{name}.png"
    fig.savefig(out_path, dpi=dpi, facecolor="black")
    plt.close(fig)

    # wymuszamy prawdziwy grayscale, zeby WP nie traktowal jako "colour"
    Image.open(out_path).convert("L").save(out_path)

    print(f"zapisano {out_path} ({len(patches)} platow, {len(lines)} linii)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", default="land_cover")
    ap.add_argument("--out", default="masks")
    ap.add_argument("--origin-x", type=float, required=True)
    ap.add_argument("--origin-y", type=float, required=True)
    ap.add_argument("--width-px", type=int, required=True)
    ap.add_argument("--height-px", type=int, required=True)
    ap.add_argument("--pixel-size", type=float, required=True)
    ap.add_argument("--dpi", type=int, default=100)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)
    indir = Path(args.indir)

    xmin, ymax = args.origin_x, args.origin_y
    xmax = xmin + args.width_px * args.pixel_size
    ymin = ymax - args.height_px * args.pixel_size
    clip = box(xmin, ymin, xmax, ymax)

    for name, (kind, lw) in LAYERS.items():
        if name in ("roads_paved", "roads_path", "roads_steps"):
            src = indir / "roads.geojson"
            if not src.exists():
                print(f"brak {src}, pomijam {name}")
                continue
            all_feats = json.loads(src.read_text(encoding="utf-8")).get("features", [])
            if name == "roads_steps":
                feats = [
                    f
                    for f in all_feats
                    if f.get("properties", {}).get("highway") == "steps"
                ]
            else:
                want_paved = name == "roads_paved"
                feats = [
                    f
                    for f in all_feats
                    if f.get("properties", {}).get("highway") != "steps"
                    and is_paved(f.get("properties", {})) == want_paved
                ]
        else:
            src = indir / f"{name}.geojson"
            if not src.exists():
                print(f"brak {src}, pomijam {name}")
                continue
            feats = json.loads(src.read_text(encoding="utf-8")).get("features", [])

        if not feats:
            print(f"{name}: brak obiektow w obszarze, pomijam")
            continue

        patches, lines = collect(feats, clip)
        if not patches and not lines:
            print(f"{name}: po przycieciu brak geometrii, pomijam")
            continue

        render(
            name,
            patches,
            lines,
            kind,
            lw,
            out_dir,
            xmin,
            xmax,
            ymin,
            ymax,
            args.width_px,
            args.height_px,
            args.dpi,
        )


if __name__ == "__main__":
    main()
