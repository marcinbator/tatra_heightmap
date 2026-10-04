#!/usr/bin/env python3
"""
Wyrownuje jeziora w heightmapie: plaskie lustro, lagodna nieczka, bez rantu.
Tam, gdzie brzeg jest nizej niz woda, usypuje lagodny nasyp do poziomu wody
(--embank-px 0 wylacza nasyp).
Zapisuje tez *_water.png: 16-bit, wartosc = id jeziora (0 = brak wody).
"""

import argparse, csv, json
import numpy as np
import rasterio
from affine import Affine
from PIL import Image
from rasterio.features import rasterize
from pyproj import Transformer
from scipy import ndimage as ndi
from shapely.geometry import shape
from shapely.ops import transform as shp_transform


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--water", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--origin-x", type=float, required=True)
    ap.add_argument("--origin-y", type=float, required=True)
    ap.add_argument("--low", type=float, default=-64)
    ap.add_argument("--high", type=float, default=426)
    ap.add_argument("--max-depth", type=float, default=8)
    ap.add_argument("--ramp-px", type=float, default=10)
    ap.add_argument(
        "--shore-percentile", type=float, default=25, help="wyzszy = wyzsze lustro"
    )
    ap.add_argument(
        "--raise", dest="raise_", type=int, default=0, help="podnies jezioro o N blokow"
    )
    ap.add_argument("--min-halfwidth-px", type=float, default=1.5)
    ap.add_argument(
        "--embank-px", type=int, default=6, help="zasieg nasypu; 0 = bez nasypu"
    )
    ap.add_argument(
        "--embank-slope",
        type=float,
        default=0.6,
        help="spadek nasypu w blokach na piksel",
    )
    args = ap.parse_args()

    with rasterio.open(args.inp) as src:
        data = src.read(1).astype(np.float32)
        src_transform, crs = src.transform, src.crs
    h, w = data.shape
    transform = Affine(
        src_transform.a, 0, args.origin_x, 0, src_transform.e, args.origin_y
    )
    to_crs = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True).transform

    feats = json.load(open(args.water, encoding="utf-8"))["features"]
    shapes, names = [], {}
    for f in feats:
        tags = f.get("properties") or {}
        if tags.get("waterway") == "riverbank" or tags.get("water") in (
            "river",
            "stream",
            "canal",
        ):
            continue
        g = f.get("geometry")
        if not g or g["type"] not in ("Polygon", "MultiPolygon"):
            continue
        try:
            geom = shape(g)
            if not geom.is_valid:
                geom = geom.buffer(0)
            geom = shp_transform(to_crs, geom)
        except Exception:
            continue
        if geom.is_empty:
            continue
        i = len(shapes) + 1
        shapes.append((geom, i))
        names[i] = tags.get("name", "") or f.get("id", "")
    print(f"poligonow wody: {len(shapes)}")

    labels = rasterize(
        shapes, out_shape=(h, w), transform=transform, fill=0, dtype="int32"
    )
    water = np.zeros((h, w), dtype=np.uint16)

    upb = 65535.0 / (args.high - args.low)
    pad = max(args.embank_px, 1) + 2
    rows, skipped = [], []
    present = set(np.unique(labels)) - {0}
    for i in range(1, len(shapes) + 1):
        if i not in present:
            skipped.append((names[i], "poza mapa albo mniejsze niz 1 px"))

    for i, sl in enumerate(ndi.find_objects(labels), start=1):
        if sl is None:
            continue
        y0, y1 = max(sl[0].start - pad, 0), min(sl[0].stop + pad, h)
        x0, x1 = max(sl[1].start - pad, 0), min(sl[1].stop + pad, w)
        lab = labels[y0:y1, x0:x1]
        sub = data[y0:y1, x0:x1]
        mask = lab == i

        dist = ndi.distance_transform_edt(mask)
        dmax = float(dist.max())
        if dmax < args.min_halfwidth_px:
            skipped.append((names[i], f"za waskie ({dmax:.1f} px)"))
            continue

        shore = ndi.binary_dilation(mask) & ~mask & (lab == 0)
        vals = sub[shore]
        vals = vals[vals > 0]
        if vals.size < 3:
            skipped.append((names[i], "brak brzegu (przy krawedzi mapy?)"))
            continue

        lvl_units = float(np.percentile(vals, args.shore_percentile))
        lvl_block = (
            round(args.low + lvl_units / 65535.0 * (args.high - args.low)) + args.raise_
        )
        lvl = (lvl_block - args.low) * upb

        depth = float(np.clip(0.15 * dmax, 2.0, args.max_depth))
        t = np.clip(dist / args.ramp_px, 0, 1)
        s = t * t * (3 - 2 * t)
        bottom = lvl - (1.0 + (depth - 1.0) * s) * upb
        sub[mask] = np.minimum(sub[mask], bottom[mask])

        if args.embank_px > 0:
            d_out = ndi.distance_transform_edt(~mask)
            target = lvl - np.maximum(d_out - 1, 0) * args.embank_slope * upb
            zone = (lab == 0) & (d_out <= args.embank_px)
            sub[zone] = np.maximum(sub[zone], target[zone])

        lake_id = len(rows) + 1
        water[y0:y1, x0:x1][mask] = lake_id

        ys, xs = np.nonzero(mask)
        rows.append(
            (
                lake_id,
                names[i],
                round(depth, 1),
                int(x0 + xs.mean()),
                int(y0 + ys.mean()),
                int(mask.sum()),
            )
        )

    out = np.clip(np.rint(data), 0, 65535).astype(np.uint16)
    with rasterio.open(
        args.out,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype="uint16",
        crs=crs,
        transform=transform,
        compress="lzw",
    ) as dst:
        dst.write(out, 1)

    base = args.out.rsplit(".", 1)[0]
    Image.fromarray(water).save(base + "_water.png")

    with open(base + "_lakes.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["id", "nazwa", "glebokosc_bloki", "swiat_x", "swiat_z", "pow_px"])
        wr.writerows(sorted(rows, key=lambda r: -r[5]))

    print(f"jezior: {len(rows)}  ->  {args.out}, {base}_water.png, {base}_lakes.csv")
    if skipped:
        print(f"pominiete ({len(skipped)}):")
        for name, why in skipped:
            print(f"  {name or '(bez nazwy)':30s} {why}")


if __name__ == "__main__":
    main()
