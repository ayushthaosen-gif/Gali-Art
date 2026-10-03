# Poster generator

Renders a real city street network (OpenStreetMap) as a label-free poster in one of the site's themes.

**Run it locally or in Google Colab.** It downloads data from the Overpass API, so it needs open internet access (it is not run in CI or in restricted sandboxes).

```bash
cd generator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python make_poster.py "Delhi, India" --theme blue --dist 12000
```

Output: `assets/delhi-blue.png` and `assets/delhi-blue.svg`. Then reference the PNG from `data/posters.json` (`"image": "assets/delhi-blue.png"`).

Colab: `!pip install osmnx matplotlib`, upload `make_poster.py`, then `!python make_poster.py "Delhi, India" --theme blue`, and download the files.

Themes live in `THEMES` at the top of the script; keep them in sync with `config.js`. Large cities with big radii can take several minutes and a lot of memory.
