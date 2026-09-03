import os
import numpy as np
import re
import time
from tqdm import tqdm


def trim_borders_tracked(data, border_value=0.0):
    def safe_all(row_or_col):
        return row_or_col.size > 0 and np.all(row_or_col == border_value)

    top, bottom, left, right = 0, 0, 0, 0
    while data.shape[0] > 0 and safe_all(data[0, :]):
        data = data[1:, :]
        top += 1
    while data.shape[0] > 0 and safe_all(data[-1, :]):
        data = data[:-1, :]
        bottom += 1
    while data.shape[1] > 0 and safe_all(data[:, 0]):
        data = data[:, 1:]
        left += 1
    while data.shape[1] > 0 and safe_all(data[:, -1]):
        data = data[:, :-1]
        right += 1

    return data, top, left


input_dir = "tatry_pl_dtm_tiles_v2"
res = 1

tiles = []
for f in os.listdir(input_dir):
    if f.endswith(".asc"):
        match = re.search(r"dtm_(-?\d+)_(-?\d+)\.asc", f)
        if match:
            x, y = map(int, match.groups())
            tiles.append((x, y, os.path.join(input_dir, f)))

print(f"Znaleziono {len(tiles)} kafli")

print("Odczyt naglowkow...")
positions = []
for x, y, path in tqdm(tiles):
    with open(path, "r") as f:
        header = {}
        for _ in range(6):
            line = f.readline().strip().split()
            if len(line) >= 2:
                header[line[0].lower()] = float(line[1])
        xllcorner = header["xllcorner"]
        yllcorner = header["yllcorner"]
        ncols = int(header["ncols"])
        nrows = int(header["nrows"])
        cellsize = header.get("cellsize", 1.0)
    positions.append((xllcorner, yllcorner, ncols, nrows, path))

min_x = min(p[0] for p in positions)
min_y = min(p[1] for p in positions)
max_x = max(p[0] + p[2] * res for p in positions)
max_y = max(p[1] + p[3] * res for p in positions)

map_width = int((max_x - min_x) / res)
map_height = int((max_y - min_y) / res)
print(f"Rozmiar mapy: {map_width} x {map_height}")

sum_map = np.zeros((map_height, map_width), dtype=np.float64)
count_map = np.zeros((map_height, map_width), dtype=np.uint16)

print("Wczytywanie i sklejanie kafli...")
for xllcorner, yllcorner, ncols, nrows, path in tqdm(positions):
    with open(path, "r") as f:
        header = {}
        for _ in range(6):
            line = f.readline().strip().split()
            if len(line) >= 2:
                header[line[0].lower()] = float(line[1])
        data = np.loadtxt(f)

    nodata = header.get("nodata_value", None)

    data = data.astype(np.float64)
    if nodata is not None:
        data[data == nodata] = np.nan

    # trim_borders na kopii z zerami (do wyznaczenia marginesow),
    # ale filtr wartosci < 100 stosujemy PO obliczeniu przesuniecia
    trim_input = np.where(np.isnan(data), 0.0, data)
    _, trimmed_top, trimmed_left = trim_borders_tracked(trim_input, border_value=0.0)

    data[data < 100] = np.nan  # artefakty

    x_start = round((xllcorner - min_x) / cellsize) + trimmed_left
    y_start = round((max_y - yllcorner) / cellsize) - nrows + trimmed_top

    # przycinamy dane o dokladnie tyle samo, o ile przesuwamy pozycje
    h, w = data.shape
    data_trimmed = data[trimmed_top:h, trimmed_left:w]

    tile_h, tile_w = data_trimmed.shape
    y_end = y_start + tile_h
    x_end = x_start + tile_w

    y0, y1 = max(0, y_start), min(map_height, y_end)
    x0, x1 = max(0, x_start), min(map_width, x_end)
    dy0, dy1 = y0 - y_start, (y0 - y_start) + (y1 - y0)
    dx0, dx1 = x0 - x_start, (x0 - x_start) + (x1 - x0)

    chunk = data_trimmed[dy0:dy1, dx0:dx1]
    valid = ~np.isnan(chunk)

    sum_map[y0:y1, x0:x1][valid] += chunk[valid]
    count_map[y0:y1, x0:x1][valid] += 1

print("Usrednianie...")
t0 = time.time()
with np.errstate(invalid="ignore", divide="ignore"):
    full_map = np.where(
        count_map > 0, sum_map / np.maximum(count_map, 1), np.nan
    ).astype(np.float32)
print(f"  ({time.time()-t0:.1f}s)")

nan_mask = np.isnan(full_map)
n_nan = np.sum(nan_mask)
print(f"Pikseli bez danych po sklejeniu: {n_nan} ({100*n_nan/full_map.size:.3f}%)")
print("NoData zostanie zachowane (uzupelni je slowacka czesc przy scaleniu)")

print("Zapis GeoTIFF...")
t0 = time.time()
import rasterio
from rasterio.transform import from_origin

transform = from_origin(min_x, max_y, res, res)

nodata_val = -9999.0
full_map_out = np.where(np.isnan(full_map), nodata_val, full_map).astype(np.float32)

with rasterio.open(
    "tatry_pl_dem_v4.tif",
    "w",
    driver="GTiff",
    height=map_height,
    width=map_width,
    count=1,
    dtype="float32",
    crs="EPSG:2180",
    transform=transform,
    nodata=nodata_val,
) as dst:
    dst.write(full_map_out, 1)
print(f"  ({time.time()-t0:.1f}s)")

print("Zapisano tatry_pl_dem_v4.tif")
