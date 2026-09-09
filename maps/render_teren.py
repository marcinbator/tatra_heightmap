#!/usr/bin/env python3
"""
Renders a land-cover PNG from the scraper's GeoJSON files, reprojected to
EPSG:2180 and aligned pixel-for-pixel with a heightmap (origin/size from
gdalinfo on that heightmap tif).

    uv run --with matplotlib --with shapely --with pyproj render_teren.py \
        --in land_cover --out terrain.png \
        --origin-x 539958.463 --origin-y 162331.572 \
        --width-px 11075 --height-px 5186 --pixel-size 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform as shp_transform

TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True)

STYLE = {
    "meadows": {
        "face": "#d5e08a",
        "edge": "none",
        "z": 1,
        "kind": "fill",
        "alpha": 0.95,
        "label": "meadows / pastures / fields",
    },
    "forest": {
        "face": "#2d6a3e",
        "edge": "none",
        "z": 2,
        "kind": "fill",
        "alpha": 0.95,
        "label": "forest",
    },
    "dwarf_pine": {
        "face": "#7a9a3a",
        "edge": "none",
        "z": 3,
        "kind": "fill",
        "alpha": 0.92,
        "label": "dwarf pine / scrub",
    },
    "rocks": {
        "face": "#9a9a96",
        "edge": "none",
        "z": 4,
        "kind": "fill",
        "alpha": 0.88,
        "label": "rocks / scree",
    },
    "glaciers": {
        "face": "#e8f4ff",
        "edge": "#c5d8ea",
        "z": 5,
        "kind": "fill",
        "alpha": 0.95,
        "label": "glaciers",
    },
    "buildings": {
        "face": "#c4b8a8",
        "edge": "none",
        "z": 6,
        "kind": "fill",
        "alpha": 0.95,
        "label": "buildings",
    },
    "water": {
        "face": "#4a90c2",
        "edge": "none",
        "z": 7,
        "kind": "fill",
        "alpha": 0.95,
        "label": "lakes / reservoirs",
    },
    "rivers": {
        "face": "#4a90c2",
        "edge": "#4a90c2",
        "z": 8,
        "kind": "line",
        "lw": 0.55,
        "alpha": 0.95,
        "label": "rivers / streams",
    },
    "roads": {
        "face": "#5a5248",
        "edge": "#5a5248",
        "z": 9,
        "kind": "line",
        "lw": 0.28,
        "alpha": 0.75,
        "label": "roads / trails",
    },
}

DRAW_ORDER = [
    "meadows",
    "forest",
    "dwarf_pine",
    "rocks",
    "glaciers",
    "buildings",
    "water",
    "rivers",
    "roads",
]


def to_2180(geom):
    return shp_transform(TRANSFORMER.transform, geom)


def load_features(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("features", [])


def polygon_path(geom) -> MplPath | None:
    verts, codes = [], []

    def add_ring(xy):
        xs, ys = xy
        pts = list(zip(xs, ys))
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
        if not verts:
            return None
        return MplPath(verts, codes)
    return None


def collect(features: list[dict], clip):
    patches, lines = [], []
    for feat in features:
        raw = feat.get("geometry")
        if not raw:
            continue
        try:
            geom = shape(raw)
            if not geom.is_valid:
                geom = geom.buffer(0)
            geom = to_2180(geom)  # reproject BEFORE clipping
            geom = geom.intersection(clip)
            if geom.is_empty:
                continue
            geoms = list(geom.geoms) if geom.geom_type.startswith("Multi") else [geom]
            for g in geoms:
                if g.geom_type == "Polygon":
                    pth = polygon_path(g)
                    if pth is not None:
                        patches.append(PathPatch(pth))
                elif g.geom_type in ("LineString", "LinearRing"):
                    lines.append(list(g.coords))
        except Exception:
            pass
    return patches, lines


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Land-cover GeoJSON to PNG, aligned to the heightmap (EPSG:2180)"
    )
    p.add_argument("--in", dest="indir", default="land_cover")
    p.add_argument("--out", default="terrain.png")
    p.add_argument(
        "--origin-x", type=float, required=True, help="heightmap origin X (from gdalinfo)"
    )
    p.add_argument(
        "--origin-y",
        type=float,
        required=True,
        help="heightmap origin Y (from gdalinfo, top-left corner)",
    )
    p.add_argument("--width-px", type=int, required=True)
    p.add_argument("--height-px", type=int, required=True)
    p.add_argument(
        "--pixel-size", type=float, required=True, help="heightmap meters/px"
    )
    p.add_argument("--dpi", type=int, default=100)
    p.add_argument("--layers", nargs="+", default=DRAW_ORDER, choices=list(STYLE))
    p.add_argument("--no-legend", dest="legend", action="store_false")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    indir = Path(args.indir)

    xmin = args.origin_x
    ymax = args.origin_y
    xmax = xmin + args.width_px * args.pixel_size
    ymin = ymax - args.height_px * args.pixel_size
    clip = box(xmin, ymin, xmax, ymax)

    fig_w = args.width_px / args.dpi
    fig_h = args.height_px / args.dpi
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=args.dpi)
    fig.patch.set_facecolor("#e8e4d8")
    ax.set_facecolor("#e8e4d8")

    used_layers = []
    for name in DRAW_ORDER:
        if name not in args.layers:
            continue
        path = indir / f"{name}.geojson"
        if not path.exists():
            print(f"missing {path}, skipping", file=sys.stderr)
            continue
        print(f"drawing {name} ...")
        feats = load_features(path)
        patches, lines = collect(feats, clip)
        st = STYLE[name]
        print(f"  {len(feats)} features -> {len(patches)} patches, {len(lines)} lines")
        if st["kind"] == "fill" and patches:
            coll = PatchCollection(
                patches,
                facecolor=st["face"],
                edgecolor="none" if st["edge"] == "none" else st["edge"],
                linewidths=0.15 if st["edge"] != "none" else 0,
                alpha=st["alpha"],
                zorder=st["z"],
            )
            ax.add_collection(coll)
        if lines:
            lc = LineCollection(
                lines,
                colors=st["edge"],
                linewidths=st.get("lw", 0.4),
                alpha=st["alpha"],
                zorder=st["z"],
                capstyle="round",
                joinstyle="round",
            )
            ax.add_collection(lc)
        used_layers.append(name)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect(1)  # meters = meters, no cosine correction (that was only for lon/lat)
    ax.axis("off")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    if args.legend and used_layers:
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D

        handles = []
        for name in used_layers:
            st = STYLE[name]
            if st["kind"] == "line":
                handles.append(
                    Line2D([0], [0], color=st["edge"], lw=2, label=st["label"])
                )
            else:
                handles.append(Patch(facecolor=st["face"], label=st["label"]))
        ax.legend(
            handles=handles,
            loc="lower left",
            frameon=True,
            fancybox=False,
            framealpha=0.92,
            fontsize=9,
        )

    out = Path(args.out)
    fig.savefig(out, dpi=args.dpi, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"saved {out.resolve()} ({args.width_px}x{args.height_px}px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
