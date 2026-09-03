# Słowacja - pobieranie i konwersja DTM

## 1. Zrodlo

Plik: dmr3_5_10.tif (1.98 GB) - caly obszar Slowacji <https://opendata.skgeodesy.sk/static/DMR3_5/dmr3_5-10.zip>

## 2. Przyciecie + reprojekcja

### Przyciecie do obszaru Tatr (z zapasem na polnoc, do 49.319372 - ta sama granica co PL)

`gdalwarp -te 19.55 49.00 20.45 49.319372 -te_srs EPSG:4326 dmr3_5_10.tif tatry_sk_crop3.tif`

### Reprojekcja Krovak -> CS92 (EPSG:2180), zeby pasowalo do polskiej czesci

`gdalwarp --config GTIFF_SRS_SOURCE EPSG -t_srs EPSG:2180 -tr 1 1 -r bilinear tatry_sk_crop3.tif tatry_sk_2180_v3.tif`

> Output: tatry_sk_2180_v3.tif
> Min=530.066m, Max=2655.259m (Gerlach), Valid=75.8%

## 3. Konwersja do 16-bit + skalowanie

`gdal_translate -ot UInt16 -scale 530.066 2655.259 0 65535 -a_nodata 0 tatry_sk_2180_v3.tif tatry_sk_v3_16bit.tif`
`gdal_translate -ot UInt16 -scale 530.066 2655.259 0 65535 -a_nodata 0 -outsize 25% 25% -r average tatry_sk_2180_v3.tif tatry_sk_v3_16bit_25pct.tif`

Skala identyczna jak w polskiej czesci (530.066-2655.259m -> 0-65535) - KLUCZOWE
zeby te same wartosci szarosci odpowiadaly tym samym wysokosciom po obu stronach.
