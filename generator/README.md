# Poster generator

Renders a real city street network (OpenStreetMap) as a label-free, print-ready poster in one of the site's themes.

**Run it locally or in Google Colab.** Road downloading uses the Overpass API, so it needs open internet access (it is not run in CI or restricted sandboxes). `--preview` skips OSM; `--extent-auto` still needs internet on the first run, and poster fonts may download if not cached.

```bash
cd generator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python make_poster.py --preview --size a4 --dpi 100            # offline look-and-feel test, synthetic network
python make_poster.py --place "Delhi, India" --theme blue --size 18x24
python make_poster.py --point 28.6139 77.2090 --dist 9000 --city-name Delhi --size a3
python make_poster.py --place "Delhi, India" --size a3 --bleed-mm 3   # print-shop file
python make_poster.py --place "Guwahati, Assam, India" --city-name Guwahati --region "Assam, India" --theme blue --size a3   # Guwahati (check the printed area first)
```

Output goes to `assets/<name>-<year>-<theme>-<size>.pdf` and `.png` (e.g. `assets/delhi-2025-blue-18x24.pdf`).

## Layout
Layout 1a from the design spec: map 80% of the width centred with its top edge at 12% of the width, then a footer anchored 10% of the width above the bottom: city, fine rule, region, coordinates, map year. **All measurements live in `data/layout.json`**, which the website reads too, so edit it there and both change together. Footer text is set in Jost and DM Mono (open licence); the script downloads them into `generator/fonts/` on first run and falls back to a system font with a warning if it can't.

Optional personal date line (weddings, moves, births): `--date "14 FEB 2026"`, printed under the year in the same small type.

Personalisation: `--detail "Where we met"` (the short line under the data, max 40 characters), `--edition 14/100` (prints `NO. 14 / 100`), `--mark LAT LON --mark-style dot|ring|heart` (marks a place, with a background-coloured halo so it reads over dense streets), and `--address "Hauz Khas Village, Delhi"` (geocode a place and centre on it, like `--point`; use `--dist` for the size of the area, about 5000 for a neighbourhood and 2000 for street level). The footer text can't shape non-Latin scripts such as Devanagari; the script warns if you try.

Footer text: `--city-name`, `--region`, `--coords LAT LON`, `--year`. Defaults come from `--place` ("Delhi, India" gives DELHI / INDIA) and a built-in list of recognisable city centres. `--year` only changes the label: the road data is always current OpenStreetMap. The optional extent filter below approximates a past city's footprint; real historical street maps need archival data.

- **PDF is the print master** (vector, exact page size). PNG is 300 dpi by default: A3 = 3508×4961 px, 18×24 in = 5400×7200 px. For the website use a small PNG (`--dpi 100`) and reference it from `data/posters.json` (`"image": "assets/delhi-blue-a3.png"`).
- **Website map mask:** `--formats mask` writes `assets/<name>-<year>-lines.png`, white streets on a transparent background. The website recolours it per theme. It has no footer and also works with the city extent filter. To use it, convert to WebP if you like, put it in `assets/`, and add it to the city in `config.js`, e.g. `maps: { "2025": "assets/mumbai-lines.webp" }` (one entry per map year; years without one show the placeholder pattern).
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

## Built-up extent approximation

**This is a "city extent" approximation: modern roads within the historic built-up area, not the real historic street pattern. Label it "city extent" in anything customer-facing**, and identify the GHSL epoch used. GHSL is the European Commission's Global Human Settlement Layer; its satellite-derived built-up surface estimates include temporal interpolation. Even an exact epoch is an estimated extent, not a surveyed historical road network.

One command downloads the required **GHS-BUILT-S R2023A**, **100 m**, **World Mollweide (ESRI:54009)** tile(s), caches them, filters the roads, and exports the website mask:

```bash
python make_poster.py --place "Delhi, India" --year 1995 --extent-auto --formats mask
python make_poster.py --place "Delhi, India" --year 1970 --extent-auto --formats pdf,png --max-tier 3
```

GHSL epochs are five-yearly from **1975**. **1995** is an exact epoch. This downloader selects the nearest epoch in **1975–2020** and prints it; ties prefer the earlier epoch, and later requested years use 2020 rather than the product's 2025/2030 extrapolations. Years **before 1973 are rejected**, with **1970 explicitly allowed as a 1975 proxy** for the site's edition; disclose that five-year difference. **1920 and 1945 cannot be approximated this way** and require another source. Invalid years are rejected before any road or raster download.

ZIPs and extracted GeoTIFFs live in the ignored `generator/cache/ghsl/`. Downloads show progress, use a 60-second socket timeout, and make at most four attempts with 1/2/4-second backoff. Interrupted transfers resume with HTTP Range when supported; if the server ignores Range, they restart safely. HTML/error responses and ZIPs failing CRC checks are rejected. Extraction promotes files atomically after checking CRS, cell size and bounds; valid cached TIFFs need no HTTP requests. All selected tiles must collectively cover the requested road bounding box.

**Measured on 2026-10-03:** Delhi 1995 uses **R6_C26**. The actual downloaded ZIP was **16,134,435 bytes (15.39 MiB)**; the extracted TIFF was **15,809,263 bytes (15.08 MiB)**, about **30.47 MiB** combined cache storage. Other epochs and cities vary; crossing a tile boundary downloads multiple archives. This tile has 10,000 × 10,000 cells; a full uncompressed UInt16 band is about 191 MiB, but the filter reads/mosaics only the roads' window. India Gate (77.2295 E, 28.6129 N) measured **1,101 m²** built-up surface in its 1995 cell.

Manual files also work; repeat `--extent-raster` for adjoining tiles with matching CRS/cell grid. It is mutually exclusive with `--extent-auto`. The CLI reports the expected epoch, but **does not infer or validate the epoch of manually supplied files**. Get them from the [official GHSL download page](https://ghsl.jrc.ec.europa.eu/download.php), selecting GHS-BUILT-S R2023A, 100 m, the epoch and city tile(s), then unzip the `.tif`. Roads outside manual raster coverage are excluded.

```bash
python make_poster.py --place "Delhi, India" --year 1995 --extent-raster GHS_BUILT_S_E1995_....tif --formats mask
python make_poster.py --preview --year 1995 --extent-raster local-west.tif --extent-raster local-east.tif --size a4 --dpi 100 --formats mask
python fetch_ghsl.py --bbox 77.20 28.58 77.26 28.65 --year 1995
python test_extent.py
python test_fetch_ghsl.py
```

`--extent-threshold` defaults to **500 m²** per cell. `--extent-buffer` defaults to **3 cells** of morphological closing (bridges narrow gaps, not a uniform outward buffer); holes are filled. `--extent-min-blob` removes connected blobs smaller than **30 cells**. Each road segment is kept when its middle vertex falls inside the cleaned extent; this does not clip segments at the boundary. `--max-tier N` optionally keeps only tiers 1 through N, and also works without a raster. Fewer than 5% retained triggers a coverage/threshold warning; an empty result stops rendering.

The extent test creates two synthetic EPSG:4326 discs around India Gate, checks middle-vertex and tier filtering against the EPSG:32643 preview network, compares split-tile mosaics to a single raster, and exercises PDF, PNG and mask output. It substitutes system fonts to avoid font downloads. The downloader test uses mock HTTP for download, resume, retries, ZIP validation and caching, and checks epoch/grid selection offline. Neither script downloads OSM or GHSL.

### Verified grid and URLs

The URL template in `fetch_ghsl.py` was checked against the [JRC R2023A directory](https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_S_GLOBE_R2023A/) and the [Delhi 1995 tile listing](https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_S_GLOBE_R2023A/GHS_BUILT_S_E1995_GLOBE_R2023A_54009_100/V1-0/tiles/), including a successful HEAD, partial GET (206), and complete ZIP download on **2026-10-03**. Paths use `V1-0` directories and `V1_0_R{row}_C{col}` filenames.

`ghsl_tiles.json` contains 375 land-tile rectangles derived from the DBF in the [official Mollweide tile index](https://human-settlement.emergency.copernicus.eu/download/GHSL_data_54009_shapefile.zip), with source/date metadata. The grid origin is **x = −18,041,000 m, y = 9,000,000 m**; rows increase southward, columns eastward, at **1,000,000 m** intervals, with clipped outer columns and ocean-only cells absent. Selection intersects the transformed bounding box with those actual rectangles rather than assuming every grid cell exists. Antimeridian-crossing boxes must be split.

The [GHSL Data Package 2023 report](https://human-settlement.emergency.copernicus.eu/documents/GHSL_Data_Package_2023.pdf) describes 100 × 100 km tiles, but the supplied download index and downloaded 100 m Delhi TIFF actually cover **1,000 × 1,000 km**. The downloader follows the verified index and TIFF bounds. The old GHSL page address redirects to the Copernicus domain; GHS-BUILT-S remains R2023A even though the current site includes newer releases of other products.

### Licence and attribution

The [official GHSL use conditions](https://human-settlement.emergency.copernicus.eu/GHSLhowToCite.php) specify **CC BY 4.0**, including commercial reuse with credit, an indication of changes, and no implied endorsement. They require the release's peer-reviewed reference and the relevant product citation; a generic website credit alone is insufficient. Include these in credits accompanying a city extent approximation:

- European Commission, Joint Research Centre, GHSL **GHS-BUILT-S R2023A**, selected epoch, CC BY 4.0. Changes: thresholded/cleaned built-up extent used to select modern OpenStreetMap roads; a city extent approximation, not a historical street map.
- Pesaresi, M.; Politis, P., **GHS-BUILT-S R2023A** dataset, European Commission, Joint Research Centre ([current catalogue citation](https://data.jrc.ec.europa.eu/dataset/9f06f36f-4b11-47ec-abb0-4f8b7b1d72ea), accessed 2026-10-03; catalogue citation year 2026), [DOI 10.2905/9F06F36F-4B11-47EC-ABB0-4F8B7B1D72EA](https://doi.org/10.2905/9F06F36F-4B11-47EC-ABB0-4F8B7B1D72EA).
- Pesaresi, M. et al. (2024), *Advances on the Global Human Settlement Layer by joint assessment of Earth Observation and population survey data*, International Journal of Digital Earth, 17(1), [DOI 10.1080/17538947.2024.2390454](https://doi.org/10.1080/17538947.2024.2390454).

OpenStreetMap road attribution still applies separately. Customer-facing site changes are outside this generator change.

Colab: `!pip install -r requirements.txt`, upload the generator files and shared `data/layout.json`, run with `!python make_poster.py ...`, then download the files from `assets/`.

Themes live in `THEMES` and sizes in `SIZES` at the top of the script; keep them in sync with `config.js`.

**Clean-up (on by default for `--place` runs, see `cleanup.py`):** roads are clipped to the OSM city boundary, disconnected fragments under 200 m are dropped (`--min-fragment`), named Lutyens' Delhi radials (list in `cleanup.py`) are held at tier 2, and rivers/lakes get a faint tint of the line colour (print poster only, not the web mask). Boundary and water are downloaded once and cached as GeoJSON in `generator/cache/`. Use `--no-cleanup` to skip all of it or `--no-water` for just the tint. Test: `python test_cleanup.py`.

## Live marker and area box on the website

The order form can place a marker and draw the 5 km / 2 km crop box from a typed address or a pasted map link. For that the site needs to know where each city map sits on the earth. Building a mask (`make_poster.py --formats mask`, or `batch_masks.py`) records it automatically in `cache/georef/<name>-<year>.json`. `python city_geo.py` (also run by `batch_masks.py --write-config`) turns those into `../data/geo.json`, a small fitted formula per city that the page loads. For maps built before this existed, `python batch_masks.py --georef` records them from the cached road data without downloading anything. A city with no entry in `geo.json` still works: the form says live placement isn't ready and the order is placed by hand from the customer's text.

## Local poster tool

A web page on your own computer that runs `make_poster.py` for you, so you can make a poster whenever you like without typing commands.

```powershell
cd generator
.\start-tool.bat          # opens http://127.0.0.1:8800 ; or: .venv\Scripts\python.exe tool.py
```

- **Where:** pick one of the maps you already have (every city in `cities.json` plus earlier custom ones, read from `cache/`, no download), or search a place, paste a Google, Apple or OpenStreetMap link (short `maps.app.goo.gl` links work), or type `latitude, longitude`.
- **How much map:** a square around the centre (half-width in km) or the whole outline of a city or district.
- **Look:** the eight themes, A4/A3/18×24, bleed, resolution, title, line under it, year, date, detail line, edition, and an optional marker (heart, dot or ring) placed from a name, link or coordinates.
- **Preview** makes a small 60 dpi PNG in seconds. **Build print file** makes the PNG and PDF (plus the transparent map if ticked).
- Files go to `print-files/<title>/` (previews in `print-files/previews/`). Recent builds, with a "use these settings again" button, are listed on the page and kept in `generator/tool_jobs.json`.
- One build runs at a time, so the OpenStreetMap server is not hammered. A new place is downloaded once, then cached in `generator/cache/`.
- The server only listens on 127.0.0.1 and refuses other host names. Place search uses OpenStreetMap's Nominatim, one request a second.
- Maps made here never touch the website: `print-files/` is git-ignored and the tool deletes the map-position files it creates.
