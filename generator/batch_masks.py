"""Batch-build web masks for the cities in cities.json (resumable), then register them in ../config.js.

  python batch_masks.py                  # build every city whose assets/<id>-lines.webp is missing
  python batch_masks.py --only mumbai pune
  python batch_masks.py --write-config   # rewrite config.js `cities` from cities.json + existing masks

Per city: checks the resolved OSM area first (skips obvious mismatches, see MIN_KM2/MAX_KM2), runs
make_poster.py --formats mask, shrinks the PNG to a 1100 px WebP in ../assets/. Results go to
cache/batch_results.json. Needs internet; a big city can take many minutes.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
TMP = HERE / "cache" / "masks"
RESULTS = HERE / "cache" / "batch_results.json"
MIN_KM2 = 15
MAX_KM2 = {"India": 1000}              # default 1700. Above this Nominatim usually returned a whole district/state
DEFAULT_MAX_KM2 = 1700
DEFAULT_DIST = 9000                  # half-width in metres of the square used when no usable city boundary exists
COMMENT = '    // maps: { "<era id>": "<path to white-lines-on-transparent PNG/WebP>" }. A city/year without an entry\n    // shows the generated placeholder pattern. Make masks with: generator/batch_masks.py (or make_poster.py --formats mask)\n'
DELHI = {"id": "delhi", "name": "Delhi", "region": "India", "lat": 28.6139, "lon": 77.2090, "seed": 11,
         "maps": {"1995": "assets/delhi-1995-lines.webp", "2025": "assets/delhi-lines.webp"}}


def load_cities():
    return json.loads((HERE / "cities.json").read_text(encoding="utf-8"))["cities"]


def area_km2(place):
    import osmnx as ox
    gdf = ox.geocode_to_gdf(place)
    return gdf.to_crs(gdf.estimate_utm_crs()).area.iloc[0] / 1e6, gdf.iloc[0]["display_name"]


def build(c, timeout_s):
    out = ASSETS / f"{c['id']}-lines.webp"
    if out.exists():
        return {"status": "exists"}
    try:
        km2, shown = area_km2(c["place"])
    except Exception as exc:
        km2, shown = None, f"no polygon ({str(exc)[:40]})"
    limit = MAX_KM2.get(c["region"], DEFAULT_MAX_KM2)
    use_place = km2 is not None and MIN_KM2 <= km2 <= limit
    mode = "boundary" if use_place else f"square {c.get('dist', DEFAULT_DIST) / 1000:g} km half-width"
    print(f"  resolved: {shown} ({"-" if km2 is None else format(round(km2), ",")} km2) -> {mode}", flush=True)
    TMP.mkdir(parents=True, exist_ok=True)
    where = ["--place", c["place"]] if use_place else ["--point", str(c["lat"]), str(c["lon"]), "--dist", str(c.get("dist", DEFAULT_DIST))]
    cmd = [sys.executable, str(HERE / "make_poster.py"), *where, "--city-name", c["name"],
           "--region", c["region"], "--coords", str(c["lat"]), str(c["lon"]), "--name", c["id"],
           "--formats", "mask", "--out", str(TMP)]
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=timeout_s)
    png = TMP / f"{c['id']}-2025-lines.png"
    if r.returncode or not png.exists():
        return {"status": "failed", "mode": mode, "error": (r.stderr or r.stdout)[-400:]}
    from PIL import Image
    im = Image.open(png)
    im = im.resize((1100, round(im.height * 1100 / im.width)), Image.LANCZOS)
    im.save(out, "WEBP", quality=80, method=6)
    png.unlink()
    return {"status": "ok", "mode": mode, "km2": km2 and round(km2), "resolved": shown, "kb": out.stat().st_size // 1024}


def write_config(cities):
    path = HERE.parent / "config.js"
    text = path.read_text(encoding="utf-8")
    facts_path = HERE / "city_facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8")) if facts_path.exists() else {}
    entries = [DELHI] + [dict(c, seed=20 + i, maps={"2025": f"assets/{c['id']}-lines.webp"})
                         for i, c in enumerate(cities) if (ASSETS / f"{c['id']}-lines.webp").exists()]
    rows = []
    for c in entries:
        f = facts.get(c["id"])
        fact_js = ("      facts: { " + ", ".join(f"{k}: {v}" for k, v in f.items()) + " },\n") if f else ""
        maps_js = ", ".join(f'"{y}": "{p}"' for y, p in c["maps"].items())
        rows.append(f'    {{ id: "{c["id"]}", name: "{c["name"]}", seed: {c["seed"]}, region: "{c["region"]}", '
                    f'lat: {c["lat"]}, lon: {c["lon"]},\n{fact_js}      maps: {{ {maps_js} }} }}')
    block = "  cities: [\n" + COMMENT + ",\n".join(rows) + "\n  ],"
    new, n = re.subn(r"  cities: \[.*?\n  \],", lambda m: block, text, count=1, flags=re.S)
    if n != 1:
        sys.exit("Could not find the cities block in config.js")
    path.write_text(new, encoding="utf-8")
    print(f"config.js: {len(entries)} cities (Delhi + {len(entries) - 1})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="City ids to build")
    ap.add_argument("--write-config", action="store_true")
    ap.add_argument("--timeout-min", type=int, default=45)
    args = ap.parse_args()
    cities = load_cities()
    if args.write_config:
        return write_config(cities)
    results = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    for c in cities:
        if args.only and c["id"] not in args.only:
            continue
        print(f"[{c['id']}]", flush=True)
        t0 = time.time()
        try:
            res = build(c, args.timeout_min * 60)
        except Exception as exc:  # keep going; one bad city must not stop the batch
            res = {"status": "failed", "error": str(exc)[-400:]}
        res["minutes"] = round((time.time() - t0) / 60, 1)
        print(f"  -> {res['status']} {res.get('kb', '')}", flush=True)
        if res["status"] != "exists":
            results[c["id"]] = res
            RESULTS.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
