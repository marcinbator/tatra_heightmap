# Poland - downloading and converting DTM

## 1. Download

Source: geoportal.gov.pl, WCS service (NMT GRID1, DTM_PL-KRON86-NH)

Script: `download_geoportal.py`

- Range: coords_wgs84 from 19.55E-20.45E, 49.00N-49.319372N
- Method: 2645m tiles with a 20m overlap, .asc format (AAIGrid), CRS EPSG:2180, 1m resolution
- Output: .asc files in this folder (350 tiles)
- Run with: `uv run download_geoportal.py` (resumable, skips already downloaded files)

## 2. Conversion

Script: `convert.py`

- Loads all .asc files, filters NODATA_value + artifacts (<100m)
- Merges with averaging in overlap areas (sum_map/count_map)
- Output: tatry_pl_dem_v4.tif (Float32, meters, EPSG:2180, NoData=-9999)
  Min=748.96m, Max=2558.39m, Valid=16.64% (the rest is outside the PL data coverage)

## 3. Conversion to 16-bit + scaling

`gdal_translate -ot UInt16 -scale 530.066 2655.259 0 65535 -a_nodata 0 tatry_pl_dem_v4.tif tatry_pl_v4_16bit.tif`
`gdal_translate -ot UInt16 -scale 530.066 2655.259 0 65535 -a_nodata 0 -outsize 25% 25% -r average tatry_pl_dem_v4.tif tatry_pl_v4_16bit_25pct.tif`

IMPORTANT: the scaling range 530.066-2655.259 is the COMBINED PL+SK range (not just PL),
so that the same shades of gray correspond to the same elevation on both sides of the border.
