import os
import math
import requests
from pyproj import Transformer
from tqdm import tqdm

# Szerszy zakres - obejmuje Gubałówkę (do 49.319372) i zachód po Rohacze
coords_wgs84 = [
    (49.319372, 19.55),
    (49.319372, 20.45),
    (49.00000, 20.45),
    (49.00000, 19.55),
]

transformer = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True)
coords_2180 = [transformer.transform(lon, lat) for lat, lon in coords_wgs84]

min_x = min(c[0] for c in coords_2180)
max_x = max(c[0] for c in coords_2180)
min_y = min(c[1] for c in coords_2180)
max_y = max(c[1] for c in coords_2180)

tile_size = 2645  # sprawdzony rozmiar z poprzedniego udanego pobrania
overlap = 20  # NOWOŚĆ: zakładka między kaflami w metrach, żeby uniknąć szwów

output_dir = "tatry_pl_dtm_tiles_v2"
os.makedirs(output_dir, exist_ok=True)

url_template = (
    "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModel"
)
params_template = {
    "service": "wcs",
    "request": "GetCoverage",
    "version": "1.0.0",
    "coverage": "DTM_PL-KRON86-NH",
    "format": "image/x-aaigrid",
    "resx": "1",
    "resy": "1",
    "crs": "EPSG:2180",
}

n_x = math.ceil((max_x - min_x) / tile_size)
n_y = math.ceil((max_y - min_y) / tile_size)

x = min_x
with tqdm(total=n_x * n_y) as pbar:
    while x < max_x:
        y = min_y
        while y < max_y:
            # zakładka: rozszerz każdy kafel o overlap w każdą stronę
            x1 = max(min_x, x - overlap)
            y1 = max(min_y, y - overlap)
            x2 = min(x + tile_size + overlap, max_x)
            y2 = min(y + tile_size + overlap, max_y)

            bbox = f"{x1},{y1},{x2},{y2}"
            params = params_template.copy()
            params["bbox"] = bbox

            filename = os.path.join(output_dir, f"dtm_{int(x1)}_{int(y1)}.asc")

            if os.path.exists(filename):
                y += tile_size
                pbar.update(1)
                continue

            try:
                response = requests.get(url_template, params=params, timeout=90)
                response.raise_for_status()
                with open(filename, "wb") as f:
                    f.write(response.content)
            except Exception as e:
                print(f"Blad pobierania {bbox}: {e}")

            y += tile_size
            pbar.update(1)
        x += tile_size
