# Land cover overlays (OSM) and lakes

Source: OpenStreetMap via Overpass API: forest, rocks/scree, dwarf pine, water, rivers, roads (incl. `highway=steps`), buildings, meadows, glaciers.

All scripts below use the corrected heightmap grid: origin **541503.463 / 161486.572**, 11075×5186 px, 5 m/px (see main README).

## 1. Download

Script: `scrap.py`

- Downloads each layer as GeoJSON to `land_cover/*.geojson` (+ merged `all.geojson`)
- Resumable; `--force` re-downloads, `--layers roads ...` limits layers
- bbox: lon 19.55-20.45E, lat 49.00-49.319372N

```powershell
uv run scrap.py --out land_cover
```

## 2. Colour overlay (reference for hand painting)

```powershell
uv run --with matplotlib --with shapely --with pyproj render_teren.py `
    --in land_cover --out terrain_2180.png `
    --origin-x 541503.463 --origin-y 161486.572 `
    --width-px 11075 --height-px 5186 --pixel-size 5
```

## 3. Layer masks

Script: `render_masks.py` — one grayscale mask per layer in `masks/` (white = layer). Roads are split by `highway` + `surface`: `roads_paved` (asphalt, also e.g. Palenica–Morskie Oko), `roads_path`, `roads_steps`. Line widths are set in `LAYERS` at the top of the script.

```powershell
uv run --with matplotlib --with shapely --with pyproj --with pillow render_masks.py `
    --in land_cover --out masks `
    --origin-x 541503.463 --origin-y 161486.572 `
    --width-px 11075 --height-px 5186 --pixel-size 5
```

## 4. Lakes

Script: `fix_lakes.py` — carves a smooth basin for every lake into the heightmap and writes:

- `..._jeziora.tif` — heightmap to import into WorldPainter
- `..._jeziora_water.png` — lake IDs for `worldpainter/scripts/flood_lakes.js`
- `..._jeziora_lakes.csv` — lake list with world coordinates

```powershell
uv run --with rasterio --with numpy --with scipy --with shapely --with pyproj --with pillow fix_lakes.py `
    --in ..\tatry_full_16bit_20pct.tif --water land_cover\water.geojson `
    --out ..\tatry_full_16bit_20pct_jeziora.tif `
    --origin-x 541503.463 --origin-y 161486.572 --low -64 --high 426 `
    --embank-px 0 --shore-percentile 5
```

Always use the original `tatry_full_16bit_20pct.tif` as `--in`. Water itself is set inside WorldPainter by `worldpainter/scripts/flood_lakes.js` (see `worldpainter/README.md`).

WorldPainter runs scripts in an ES5 engine: no trailing commas in function calls (`.prettierrc`: `{ "trailingComma": "none" }`).
