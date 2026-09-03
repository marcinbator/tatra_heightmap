# Polska - pobieranie i konwersja DTM

## 1. Pobieranie

Zrodlo: geoportal.gov.pl, usluga WCS (NMT GRID1, DTM_PL-KRON86-NH)

Skrypt: `download_geoportal.py`

- Zakres: coords_wgs84 od 19.55E-20.45E, 49.00N-49.319372N
- Metoda: kafle 2645m z zakladka (overlap) 20m, format .asc (AAIGrid), CRS EPSG:2180, rozdzielczosc 1m
- Output: pliki .asc w tym folderze (350 kafli)
- Uruchomienie: `uv run download_geoportal.py` (wznawialny - pomija juz pobrane pliki)

## 2. Konwersja

Skrypt: `convert.py`

- Wczytuje wszystkie .asc, filtruje NODATA_value + artefakty (<100m)
- Sklejanie z usrednianiem na obszarach zakladki (sum_map/count_map)
- Output: tatry_pl_dem_v4.tif (Float32, metry, EPSG:2180, NoData=-9999)
  Min=748.96m, Max=2558.39m, Valid=16.64% (reszta poza zasiegiem PL danych)

## 3. Konwersja do 16-bit + skalowanie

`gdal_translate -ot UInt16 -scale 530.066 2655.259 0 65535 -a_nodata 0 tatry_pl_dem_v4.tif tatry_pl_v4_16bit.tif`
`gdal_translate -ot UInt16 -scale 530.066 2655.259 0 65535 -a_nodata 0 -outsize 25% 25% -r average tatry_pl_dem_v4.tif tatry_pl_v4_16bit_25pct.tif`

WAZNE: zakres skalowania 530.066-2655.259 to WSPOLNY zakres PL+SK (nie tylko PL!),
zeby te same odcienie szarosci = ta sama wysokosc po obu stronach granicy.
