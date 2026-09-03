# Tatry MC PL+SK

## 1. Pobieranie i konwersja map PL i SK

1. Zgodnie z instrukcjami w folderach `polska` i `slowacja` pobrać dane.
2. Uruchomić odpowiednie skrypty konwersji danych.

## 2. Łączenie map

1. Plik `tatry_full_16bit_25pct.tif` zawiera połączone w .xcf (Gimp) mapy 16bit pomniejszone o 75% (1/4 rozmiaru rzeczywistego).
2. Aby zmniejszyć plik wynikowy, wykonać np.:

`gdal_translate -outsize 80% 80% -r average tatry_full_16bit_25pct.tif tatry_full_16bit_20pct.tif`

## 3. Import WorldPainter

1. Ustawienia (skala 1:1 wysokość/szerokość, można wyższy high mapping):

- dla mapy 25%: scale 100%, low mapping: -64, high mapping: 480
- dla mapy 20%: scale 100%, low mapping: -64, high mapping: 368
