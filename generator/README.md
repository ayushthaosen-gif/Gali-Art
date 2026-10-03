# Poster generator

Renders a real city street network (OpenStreetMap) as a label-free, print-ready poster in one of the site's themes.

**Run it locally or in Google Colab.** Downloading uses the Overpass API, so it needs open internet access (it is not run in CI or restricted sandboxes). `--preview` needs no network.

```bash
cd generator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python make_poster.py --preview --size a4 --dpi 100            # offline look-and-feel test, synthetic network
python make_poster.py --place "Delhi, India" --theme blue --size 18x24
python make_poster.py --point 28.6139 77.2090 --dist 9000 --city-name Delhi --size a3
python make_poster.py --place "Delhi, India" --size a3 --bleed-mm 3   # print-shop file
```

Output goes to `assets/<name>-<year>-<theme>-<size>.pdf` and `.png` (e.g. `assets/delhi-2025-blue-18x24.pdf`).

## Layout
Layout 1a from the design spec: map 80% of the width centred with its top edge at 12% of the width, then a footer anchored 10% of the width above the bottom: city, fine rule, region, coordinates, map year. **All measurements live in `data/layout.json`**, which the website reads too, so edit it there and both change together. Footer text is set in Jost and DM Mono (open licence); the script downloads them into `generator/fonts/` on first run and falls back to a system font with a warning if it can't.

Optional personal date line (weddings, moves, births): `--date "14 FEB 2026"`, printed under the year in the same small type.

Footer text: `--city-name`, `--region`, `--coords LAT LON`, `--year`. Defaults come from `--place` ("Delhi, India" gives DELHI / INDIA) and a built-in list of recognisable city centres. `--year` only changes the label: the road data is always current OpenStreetMap, so historical maps (1920 to 1995) need archival data.

- **PDF is the print master** (vector, exact page size). PNG is 300 dpi by default: A3 = 3508×4961 px, 18×24 in = 5400×7200 px. For the website use a small PNG (`--dpi 100`) and reference it from `data/posters.json` (`"image": "assets/delhi-blue-a3.png"`).
- **Website map mask:** `--formats mask` writes `assets/<name>-<year>-lines.png`, white streets on a transparent background. The website recolours it per theme. To use it, convert to WebP if you like, put it in `assets/`, and add it to the city in `config.js`, e.g. `maps: { "2025": "assets/mumbai-lines.webp" }` (one entry per map year; years without one show the placeholder pattern).
- **SVG** is available (`--formats pdf,png,svg`) but can be hundreds of MB for a large city.
- **Sizes:** `a4`, `a3`, `18x24`, or any `WxH` in inches (e.g. `12x16`).
- **Line widths** scale with poster width, so every size looks alike. `--min-width` (default 0.25 pt) stops hairlines that printers drop.
- **Roads:** drivable network only. Five tiers by OSM class (motorway/trunk, primary, secondary, tertiary, residential/unclassified/living street); service roads, tracks and paths are dropped. Widths come from `layout.json` as a share of poster width, never thinner than 0.25 pt. Minor streets use a solid mix of the line colour and background (no transparency); round caps and joins.
- **Bleed:** `--bleed-mm 3` adds bleed on every side and fills it with the background; footer and map positions are unchanged relative to the trim.
- **Cache:** the downloaded graph is saved in `generator/cache/` (git-ignored), so changing theme or size doesn't re-download.

## Before a full Delhi run
1. The script prints what `--place` resolved to and its area. Delhi NCT should be about 1,480 km². If not, use a more specific place name or `--point`.
2. Test the look on a small area first (`--point ... --dist 5000`). The full territory can take several minutes and a lot of memory; if Overpass times out, retry or use a Geofabrik extract.
3. Print a small crop at real scale before ordering a big batch: screens are misleading for hairlines.

Colab: `!pip install osmnx matplotlib`, upload `make_poster.py`, run it with `!python make_poster.py ...`, then download the files from `assets/`.

Themes live in `THEMES` and sizes in `SIZES` at the top of the script; keep them in sync with `config.js`.

**Not done yet (from the design notes):** the Yamuna water fill, clipping roads to the city boundary, and dropping disconnected fragments under ~200 m.
