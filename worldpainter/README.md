# WorldPainter workflow

Backup the `.world` file (and the Minecraft world, if merging) before each step that rewrites heights.

## 1. Heightmap

`File → Import → Height map` → `tatry_full_16bit_20pct_jeziora.tif` (output of `maps/fix_lakes.py`)

- scale 100%, offset 0,0
- low mapping -64, high mapping 426
- build limits: -64 … at least 448

## 2. Lakes (water)

`Tools → Run script...` → `worldpainter/scripts/flood_lakes.js`, argument: full path to `tatry_full_16bit_20pct_jeziora_water.png`

- Water level = lowest part of the shore, gentle shore profile, gaps in the shore filled
- Knobs at the top of the script: `SHORE_PCT` (water height), `SLOPE` (shore steepness)
- Can be re-run on the same world

## 3. Lake biome and bottom

- Biome: Meadow (dark blue water, no freezing, no drowned)
- Terrain: Custom Terrain → Mixed material „Dno stawu”: Gravel 45, Stone 25, Andesite 15, Cobblestone 10, Mossy Cobblestone 5
- Apply both with Fill / big brush, filter **only on → Water**

## 4. Layers from masks

`Edit → Import → Mask as terrain or layer`, for each file in `maps/masks/`: scale 100%, offset 0,0, threshold mapping (~128).

| mask                                      | target                                                                                                                       |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `mask_forest.png`                         | layer Las                                                                                                                    |
| `mask_dwarf_pine.png`                     | layer Kosodrzewina                                                                                                           |
| `mask_rivers.png`                         | layer Rzeka / Rzeczka                                                                                                        |
| `mask_roads_paved.png`                    | layer Asfalt                                                                                                                 |
| `mask_roads_path.png`                     | layer Sciezka                                                                                                                |
| `mask_roads_steps.png`                    | layer Schody (Custom Ground Cover: Stone 40, Andesite 25, Cobblestone 20, Stone Bricks 15) — above Sciezka in the layer list |
| `mask_rocks.png`, `mask_meadows.png`, ... | terrain or layers of choice                                                                                                  |

Masks must be grayscale (the script saves them that way); colour PNGs can only go to Annotations.

## 5. Remove forest from rivers and paths

`Tools → Global operations` → Remove a layer: Las, filter only on: Rzeka (repeat for Rzeczka, Sciezka, Asfalt). Fill + right click ignores the filter and removes the whole connected forest.

Alternative script (`Tools → Run script...`), layer names must match exactly:

```javascript
var las = wp.getLayer().fromWorld(world).withName("Las").go();
var pod = ["Rzeka", "Rzeczka", "Sciezka", "Asfalt"];
for (var i = 0; i < pod.length; i++) {
  var warstwa = wp.getLayer().fromWorld(world).withName(pod[i]).go();
  var filtr = wp.createFilter().onlyOnLayer(warstwa).go();
  wp.applyLayer(las).toWorld(world).toLevel(0).withFilter(filtr).go();
}
```

## 6. Overlay for hand painting

`View → Configure overlay` → `maps/terrain_2180.png` or `ortofoto_tatry_2180.tif` — scale 100%, offset 0,0, transparency to taste. Never use „Fit to dimension”.

## 7. Export

- New world: `File → Export`
- Existing Minecraft world with builds: `File → Merge world` (Ctrl+R), never Export — read-only chunks (builds) are skipped. Backup first.
