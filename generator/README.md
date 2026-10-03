# Poster generator

Renders a real city street network (OpenStreetMap) as a label-free, print-ready poster in one of the site's themes.

**Run it locally or in Google Colab.** Downloading uses the Overpass API, so it needs open internet access (it is not run in CI or restricted sandboxes). `--preview` needs no network.

```bash
cd generator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python make_poster.py --preview --size a4 --dpi 100            # offline look-and-feel test, synthetic network
python make_poster.py --place "Delhi, India" --theme blue --size 18x24
python make_poster.py --point 28.6139 77.2090 --dist 9000 --name delhi-centre --size a3
```

Output goes to `assets/<name>-<theme>-<size>.pdf` and `.png` (e.g. `assets/delhi-blue-18x24.pdf`).

- **PDF is the print master** (vector, exact page size). PNG is 300 dpi by default: A3 = 3508×4961 px, 18×24 in = 5400×7200 px. For the website use a small PNG (`--dpi 100`) and reference it from `data/posters.json` (`"image": "assets/delhi-blue-a3.png"`).
- **SVG** is available (`--formats pdf,png,svg`) but can be hundreds of MB for a large city.
- **Sizes:** `a4`, `a3`, `18x24`, or any `WxH` in inches (e.g. `12x16`).
- **Line widths** scale with poster width, so every size looks alike. `--min-width` (default 0.25 pt) stops hairlines that printers drop.
- **Roads:** drivable network only (no footpaths), tiered by class: motorway/trunk/primary heaviest, residential finest.
- **Cache:** the downloaded graph is saved in `generator/cache/` (git-ignored), so changing theme or size doesn't re-download.

## Before a full Delhi run
1. The script prints what `--place` resolved to and its area. Delhi NCT should be about 1,480 km². If not, use a more specific place name or `--point`.
2. Test the look on a small area first (`--point ... --dist 5000`). The full territory can take several minutes and a lot of memory; if Overpass times out, retry or use a Geofabrik extract.
3. Print a small crop at real scale before ordering a big batch: screens are misleading for hairlines.

Colab: `!pip install osmnx matplotlib`, upload `make_poster.py`, run it with `!python make_poster.py ...`, then download the files from `assets/`.

Themes live in `THEMES` and sizes in `SIZES` at the top of the script; keep them in sync with `config.js`.
