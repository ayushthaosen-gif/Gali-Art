"""Turn the map extents recorded in cache/georef/*.json into one small formula per city for the website.

  python city_geo.py            # writes ../data/geo.json, which the website loads
  python city_geo.py --check    # also print the worst error of each fit

The website needs to know where a latitude/longitude falls on a city's map picture, and how big a 5 km or 2 km square is on
it. The picture is the poster's map box (see render_mask in make_poster.py): the streets' bounding box scaled to fit, centred
sideways and pinned to the top. A quadratic polynomial in (lon - lon0, lat - lat0) reproduces the projection to well under a
metre across a city, so the page needs no map-projection code.

Format in data/geo.json, per city id and year:  "c": [lat0, lon0],  "fx": [6 numbers], "fy": [6 numbers],  "box": [left, top, right, bottom]
  fraction x = fx . [1, u, v, u*u, u*v, v*v]   with u = lon - lon0, v = lat - lat0   (0..1 across the picture)
  fraction y = fy . [...]                       (0..1 down the picture)
  box = the part of the picture the streets can occupy, in the same fractions (outside it there is no map).
"""
import json
import sys
from pathlib import Path

import numpy as np
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
GEOREF = HERE / "cache" / "georef"


def fractions(X, Y, bounds, aspect):
    """Where projected points (metres) land on the map picture, as fractions of its width and height."""
    minx, miny, maxx, maxy = bounds
    dx, dy = maxx - minx, maxy - miny
    height = 1.0 / aspect                         # picture is 1 wide and 1/aspect tall
    if dy / dx <= height:                         # limited by width
        ax_w, ax_h = 1.0, dy / dx
    else:                                         # limited by height
        ax_h, ax_w = height, height * dx / dy
    off_x = (1.0 - ax_w) / 2.0                    # centred sideways, pinned to the top (ax.set_anchor("N"))
    fx = off_x + (np.asarray(X) - minx) / dx * ax_w
    fy = (maxy - np.asarray(Y)) / dy * ax_h / height
    return fx, fy, (off_x, 0.0, off_x + ax_w, ax_h / height)


def features(u, v):
    return np.stack([np.ones_like(u), u, v, u * u, u * v, v * v], axis=-1)


def fit_one(info):
    bounds, aspect, crs = info["bounds"], info["aspect"], info["crs"]
    to_ll = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    to_xy = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    minx, miny, maxx, maxy = bounds
    gx, gy = np.meshgrid(np.linspace(minx, maxx, 13), np.linspace(miny, maxy, 13))
    lon, lat = to_ll.transform(gx.ravel(), gy.ravel())
    lon0, lat0 = to_ll.transform((minx + maxx) / 2, (miny + maxy) / 2)
    u, v = np.asarray(lon) - lon0, np.asarray(lat) - lat0
    fx, fy, box = fractions(gx.ravel(), gy.ravel(), bounds, aspect)
    A = features(u, v)
    cx = np.linalg.lstsq(A, fx, rcond=None)[0]
    cy = np.linalg.lstsq(A, fy, rcond=None)[0]
    err_px = max(np.abs(A @ cx - fx).max(), np.abs(A @ cy - fy).max()) * 1100     # on the 1100 px web mask
    out = {"c": [round(lat0, 6), round(lon0, 6)],
           "fx": [float(f"{c:.8g}") for c in cx], "fy": [float(f"{c:.8g}") for c in cy],
           "box": [round(b, 5) for b in box]}
    return out, err_px


def main():
    check = "--check" in sys.argv
    result = {}
    for path in sorted(GEOREF.glob("*.json")):
        city, year = path.stem.rsplit("-", 1)
        info = json.loads(path.read_text(encoding="utf-8"))
        out, err = fit_one(info)
        result.setdefault(city, {})[year] = out
        if check:
            print(f"{city:14s} {year}  worst fit error {err:.3f} px of 1100")
    out_path = HERE.parent / "data" / "geo.json"
    out_path.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    print(f"{out_path}: {len(result)} cities, {out_path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
