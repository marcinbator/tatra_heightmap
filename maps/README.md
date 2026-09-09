# Land cover overlays (OSM)

Source: OpenStreetMap via Overpass API: forest, rocks/scree, dwarf pine, water, rivers, roads, buildings, meadows, glaciers.

## 1. Download

Script: `scrap.py`

- Downloads each layer as GeoJSON via Overpass (tries multiple mirrors, retries with backoff on 429/504)
- Resumable: skips a layer whose file already exists (`--force` re-downloads it)
- Range: same bbox as the heightmap, lon 19.55-20.45E, lat 49.00-49.319372N
- Output: `land_cover/*.geojson` (one file per layer: `forest`, `rocks`, `dwarf_pine`, `water`, `rivers`, `roads`, `buildings`, `meadows`, `glaciers`) + `land_cover/all.geojson` (merged)
- Run with: `uv run scrap.py --out land_cover` (add `--layers forest rocks ...` to fetch only some layers)

## 2. Render

Script: `render_teren.py`

- Renders the GeoJSON layers to a PNG, reprojected to EPSG:2180 and aligned pixel-for-pixel with a heightmap tif (origin/size read from `gdalinfo` on that tif)
- Run with:

```powershell
uv run --with matplotlib --with shapely --with pyproj render_teren.py `
    --in land_cover --out terrain_2180.png `
    --origin-x 539958.463 --origin-y 162331.572 `
    --width-px 11075 --height-px 5186 --pixel-size 5
```
