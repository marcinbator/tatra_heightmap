# Slovakia - downloading and converting DTM

## 1. Source

File: dmr3_5_10.tif (1.98 GB) - the entire territory of Slovakia <https://opendata.skgeodesy.sk/static/DMR3_5/dmr3_5-10.zip>

## 2. Cropping + reprojection

### Crop to the Tatra Mountains area (with a margin to the north, up to 49.319372 - same border as PL)

`gdalwarp -te 19.55 49.00 20.45 49.319372 -te_srs EPSG:4326 dmr3_5_10.tif tatry_sk_crop3.tif`

### Reprojection Krovak -> CS92 (EPSG:2180), to match the Polish part

`gdalwarp --config GTIFF_SRS_SOURCE EPSG -t_srs EPSG:2180 -tr 1 1 -r bilinear tatry_sk_crop3.tif tatry_sk_2180_v3.tif`

> Output: tatry_sk_2180_v3.tif
> Min=530.066m, Max=2655.259m (Gerlach), Valid=75.8%

## 3. Conversion to 16-bit + scaling

`gdal_translate -ot UInt16 -scale 530.066 2655.259 0 65535 -a_nodata 0 tatry_sk_2180_v3.tif tatry_sk_v3_16bit.tif`
`gdal_translate -ot UInt16 -scale 530.066 2655.259 0 65535 -a_nodata 0 -outsize 25% 25% -r average tatry_sk_2180_v3.tif tatry_sk_v3_16bit_25pct.tif`

Scale identical to the Polish part (530.066-2655.259m -> 0-65535) - CRUCIAL
so that the same grayscale values correspond to the same elevations on both sides.
