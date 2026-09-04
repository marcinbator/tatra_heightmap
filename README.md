# Tatry heightmap PL+SK

Project for building a heightmap of the Polish and Slovak Tatra Mountains at 1px=1m (PL) and 1px=10m (SK) resolution. The map can be used for 3D models and for creating maps for games such as Minecraft.

## 1. Downloading and converting PL and SK maps

1. Follow the instructions in the `polska` and `slowacja` folders to download the data.
2. Run the corresponding data conversion scripts.

## 2. Merging maps

1. The file `tatry_full_16bit_25pct.tif` contains the maps merged in .xcf (Gimp), 16-bit, reduced by 75% (1/4 of actual size).
2. To reduce the resulting file size, run e.g.:

`gdal_translate -outsize 80% 80% -r average tatry_full_16bit_25pct.tif tatry_full_16bit_20pct.tif`

## 3. WorldPainter import

1. Settings (1:1 height/width scale, higher high mapping is possible):

- for the 25% map: scale 100%, low mapping: -64, high mapping: 480
- for the 20% map: scale 100%, low mapping: -64, high mapping: 368

Best scale is <-64, 426>.

## 4. Ortofoto

geoportal.gov.pl and ZBGIS WCS were too unstable (timeouts). Used: Sentinel-2 cloudless (EOX), without splitting PL/SK, ~10m/px.

```powershell
gdal_translate -of GTiff -projwin 19.55 49.319372 20.45 49.00 -projwin_srs EPSG:4326 -outsize 6550 3550 "WMS:https://tiles.maps.eox.at/wms?service=WMS&request=GetMap&layers=s2cloudless-2024&styles=default&srs=EPSG:4326&format=image/jpeg" ortofoto_tatry_seamless.tif

gdalwarp -t_srs EPSG:2180 -tr 4 4 -r cubic ortofoto_tatry_seamless.tif ortofoto_tatry_2180.tif
```
