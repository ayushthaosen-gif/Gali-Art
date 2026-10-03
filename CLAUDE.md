# Gali-Art: project context

Static website + Python poster generator for a custom city street-map poster business. "Gali" is a placeholder brand name (change it only in `config.js`). First product: a minimalist Delhi poster, white streets on solid blue (#3F6BA8). Later: any city, 8 colour themes, map "years".

## Hard constraints (from the owner)
- Plain HTML/CSS/vanilla JS. No framework, no build step. Relative paths only (must work at any domain or subpath, later moving to Cloudflare Pages/Netlify).
- No secrets in the repo. All configuration lives in `config.js`.
- Mobile-first (owner tests on a phone). Accessible, fast.
- No payments implemented. Order form is UI only and POSTs to a configurable endpoint; a marked spot exists for a Razorpay/Stripe link.
- Owner works on Windows PowerShell (no `&&`, use `.venv\Scripts\Activate.ps1`). Owner is conserving Claude usage: keep sessions short, don't re-derive settled decisions.
- Only push to `main` when the owner asks; a push to `main` deploys the site.

## Repo map
```
index.html, 404.html, privacy.html   pages (single-page site; 404 is self-contained)
config.js        ALL config: brand, email, form endpoint, payment link, prices, sizes, cities (+maps), themes, eras
css/style.css    styles (Jost site font)
js/poster.js     poster preview renderer (SVG). Real map via alpha mask image, else seeded placeholder pattern
js/app.js        picker, gallery, order form, map-year selector
data/posters.json  gallery items (swap in real images here)
data/layout.json   poster layout in fractions of poster width. SHARED by js/poster.js and generator/make_poster.py
assets/          images; delhi-lines.webp = real Delhi 2025 line mask (white lines on transparent)
generator/       Python: make_poster.py, extent.py, fetch_ghsl.py, ghsl_tiles.json, tests, README.md
.github/workflows/pages.yml   deploys on push to main (copies only site files, not generator/)
```

## Poster design (from the Claude Design document "Gali Poster System")
Layout 1a: map 80% of width, centred, top edge at 12% W. Footer anchored 10% W above bottom, centred stack: CITY (Jost 7.2% W, tracking 0.42em, caps) / fine rule / REGION (1.55% W) / coordinates (DM Mono 1.4% W, e.g. `28.6139° N, 77.2090° E`) / map year / optional personal date (`14 FEB 2026`). No frame, compass, scale bar or brand mark on the front. Colours: text = rule = major roads = theme `line`; minor roads = mix(line, bg, 0.30), solid, never alpha. 5 road tiers by OSM class with widths as fractions of W, min 0.25 pt. Round caps/joins. Sizes: A4, A3 (1:1.414), 18x24 in (3:4). Bleed 3 mm (generator `--bleed-mm 3`). All values are in `data/layout.json`; edit there only.

## Website state (deployed on GitHub Pages)
- Live at `https://ayushthaosen-gif.github.io/Gali-Art/` (repo `ayushthaosen-gif/Gali-Art`). Pages source = GitHub Actions; the `github-pages` environment allows `main`.
- Style picker (8 themes, live recolour), map-year chips (1920, 1945, 1970, 1995, 2025), gallery, order form (city, size, year, theme, optional print date, name, email, notes; live price; demo mode when no endpoint).
- Delhi 2025 uses the real map mask. Any other city/year shows a generated PLACEHOLDER pattern. Real masks register per city and year in `config.js` under `cities[].maps`, e.g. `maps: { "2025": "assets/delhi-lines.webp" }`.
- Jost/DM Mono come from Google Fonts (mentioned in privacy.html). Self-hosting is an option later.

## Personalisation (added; fulfilment is manual for now)
Order form (all optional): area of map (whole city / neighbourhood ~5 km / street ~2 km) + "centre on" text; mark a special place (dot/ring/heart) + where; a dedication line (max 40 chars, Latin script); a printed date; then-and-now pair (older year + matching 2025, `pairDiscount` in `config.js`, shown only when the year is not 2025). All choices go in the order payload (`area`, `centreOn`, `mark`, `markAt`, `dedication`, `printDate`, `pair`). The web preview shows the dedication and a SAMPLE marker position (`markDemo` per city); the owner places the real one with the generator. Generator options: `--address` / `--point --dist` (custom centre), `--mark LAT LON --mark-style dot|ring|heart`, `--tagline`, `--edition 14/100` (prints `NO. 14 / 100`), `--date`. Footer text is placed glyph by glyph, so NON-LATIN SCRIPTS (e.g. Hindi) are NOT supported in the print file (the script warns); would need real text shaping (HarfBuzz) first. Test: `python generator/test_poster_options.py`.

## Generator (run locally; needs internet for OSM/Overpass; the Claude cloud sandbox blocks it)
```
cd generator; python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements.txt
python make_poster.py --preview --size a4                                   # offline look test
python make_poster.py --place "Delhi, India" --theme blue --size a3        # real poster (PDF + PNG)
python make_poster.py --place "Delhi, India" --year 1995 --extent-auto --extent-threshold 2000 --extent-min-blob 200 --formats mask
```
Outputs `assets/<name>-<year>-<theme>-<size>.pdf/.png`, or `<name>-<year>-lines.png` (white on transparent) with `--formats mask`. Road graph cached in `generator/cache/`. Fonts auto-download into `generator/fonts/` (untracked). Tests (no network): `python test_extent.py`, `python test_fetch_ghsl.py` (need rasterio, scipy).

### Historical years: IMPORTANT honesty rule
OSM has no data before ~2004. The only automated route is the GHSL "city extent" approximation: modern roads kept only inside the built-up area of a GHSL epoch (GHS-BUILT-S R2023A, 100 m, 5-yearly from 1975, Delhi tile R6_C26). It is NOT a historical street map; label it "city extent". 1995 is an exact epoch, 1970 can only use 1975, 1920 and 1945 cannot be done this way (need georeferenced archival maps traced to GeoJSON, not built yet). Threshold tuning on real Delhi data: the default 500 keeps ~93% of roads (too loose); 1000 to 3500 were compared, 2000 recommended, plus `--extent-min-blob 200` to drop outlying specks. A border-erosion bug in mask cleanup was fixed (regression test exists).

## Open TODOs
1. Generate the final Delhi 1995 mask (command above), convert to WebP (1100 px), add `"1995": "assets/delhi-1995-lines.webp"` to Delhi `maps` in `config.js`, and replace `eraNote` (it wrongly says "archival maps") with e.g. "1995 shows today's streets within Delhi's 1995 built-up area. Earlier years are coming soon." Optionally try 1970 (uses 1975 data).
2. Run the full Delhi 2025 print poster on the owner's machine and check the real Jost/DM Mono typography and line weights; print a small crop at real scale.
3. Not yet done from the design notes: Yamuna water tint (needs OSM water polygon), clip roads to the boundary, drop fragments under ~200 m, keep Lutyens' radial roads at tier 2.
4. Owner to-dos: real poster images in `posters.json`, form endpoint (Formspree or Apps Script) in `config.js`, payment link, real contact email, final brand name, real prices, finish privacy/terms text, custom domain (migration notes in README).
5. Check the live site on a phone (fonts, 1995 chip, order form, new personalise fields).
6. Not built (ideas): highlighted route from a GPX file, boundary/circle/heart crop shapes, Hindi/regional city names in print (needs text shaping), traced archival maps for 1920/1945, foil/finish options and gift packaging (printer/ops decisions).
