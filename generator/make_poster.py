#!/usr/bin/env python3
"""Render a city's street network as a minimalist, print-ready poster.

Run locally or in Google Colab: downloading needs access to the OpenStreetMap
Overpass API. Do NOT run it in a restricted/CI sandbox. (--preview needs no network.)

    pip install -r requirements.txt
    python make_poster.py --preview --size a4                   # offline look-and-feel test
    python make_poster.py --place "Delhi, India" --theme blue --size 18x24
    python make_poster.py --point 28.6139 77.2090 --dist 9000 --name delhi-centre

Outputs (default PDF master + PNG) go to ../assets/<name>-<theme>-<size>.<ext>.
The downloaded graph is cached in ./cache so changing theme/size doesn't re-download.
"""
import argparse
import math
import random
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

HERE = Path(__file__).resolve().parent

# Keep in sync with themes in ../config.js  (background, line)
THEMES = {
    "blue":       ("#3F6BA8", "#FFFFFF"),
    "dark-gold":  ("#111418", "#C9A24B"),
    "cream":      ("#F3ECDD", "#1B1B1B"),
    "forest":     ("#1F4D3A", "#EAF2E3"),
    "blush":      ("#F2D7D5", "#7A2E3A"),
    "midnight":   ("#0B1D3A", "#9FD0FF"),
    "terracotta": ("#B9553A", "#FFF1E0"),
    "mono":       ("#E4E4E4", "#222222"),
}

# Poster sizes in inches (width, height). Keep in sync with sizes in ../config.js
SIZES = {"a4": (8.27, 11.69), "a3": (11.69, 16.54), "18x24": (18.0, 24.0)}

# Line widths in points for a poster 12 in wide; scaled to the real width so every size looks alike.
BASE_WIDTHS = {
    "motorway": 1.2, "trunk": 1.0, "primary": 0.8, "secondary": 0.6, "tertiary": 0.4,
    "residential": 0.2, "unclassified": 0.2, "living_street": 0.2,
}
DEFAULT_BASE = 0.2
MARGIN = 0.06  # fraction of the page left empty on every side


def width_pt(highway, poster_w_in, min_pt):
    if isinstance(highway, list):
        highway = highway[0]
    base = BASE_WIDTHS.get(str(highway).replace("_link", ""), DEFAULT_BASE)
    return max(min_pt, base * poster_w_in / 12.0)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.split(",")[0].lower()).strip("-") or "city"


# ---------------------------------------------------------------- data

def load_edges(args):
    """Return [(coords, highway), ...] in a projected CRS (metres), plus a label."""
    import osmnx as ox

    ox.settings.timeout = 600
    ox.settings.use_cache = True
    cache = HERE / "cache"
    cache.mkdir(exist_ok=True)

    if args.point:
        lat, lon = args.point
        name = args.name or f"point-{lat:.3f}-{lon:.3f}"
        key = f"{slugify(name)}-{args.dist}"
    else:
        name = args.name or slugify(args.place)
        key = slugify(args.place)
    path = cache / f"{key}.graphml"

    if path.exists():
        print(f"Using cached graph {path}")
        G = ox.load_graphml(path)
    else:
        if args.point:
            print(f"Downloading roads within {args.dist} m of {args.point} ...")
            G = ox.graph_from_point(args.point, dist=args.dist, network_type="drive",
                                    retain_all=True, dist_type="bbox")
        else:
            gdf = ox.geocode_to_gdf(args.place)
            area = gdf.to_crs(gdf.estimate_utm_crs()).area.iloc[0] / 1e6
            print(f"Resolved '{args.place}' -> {gdf.iloc[0]['display_name']} ({area:,.0f} km2)")
            print("Check this is the area you expect (Delhi NCT is ~1,480 km2). Downloading ...")
            G = ox.graph_from_place(args.place, network_type="drive", retain_all=True)
        G = ox.project_graph(G)
        ox.save_graphml(G, path)
        print(f"Cached graph to {path}")

    edges = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)
    out = [(list(g.coords), hw) for g, hw in zip(edges.geometry, edges["highway"])]
    print(f"{len(out):,} road segments")
    return out, name


def synthetic_edges(seed=7):
    """Offline stand-in network for tuning look-and-feel (--preview). Not a real map."""
    r = random.Random(seed)
    ang = math.radians(-12)
    ca, sa = math.cos(ang), math.sin(ang)
    size, step = 20000, 160

    def rot(x, y):
        return (x * ca - y * sa, x * sa + y * ca)

    def steps():
        out, p = [], 0.0
        while p < size:
            out.append(p)
            p += step * (0.6 + r.random() * 0.8)
        return out

    xs, ys = steps(), steps()
    out = []
    for i, x in enumerate(xs[:-1]):
        for j, y in enumerate(ys[:-1]):
            for (x2, y2, major) in ((xs[i + 1], y, j % 9 == 0), (x, ys[j + 1], i % 9 == 0)):
                if major or r.random() < 0.85:
                    hw = "primary" if major else r.choice(["residential"] * 6 + ["tertiary", "secondary"])
                    out.append(([rot(x, y), rot(x2, y2)], hw))
    for _ in range(4):  # a few long diagonals
        d, px, py = r.uniform(0.5, 1.2), r.uniform(4000, 16000), r.uniform(4000, 16000)
        out.append(([rot(px - 12000 * math.cos(d), py - 12000 * math.sin(d)),
                     rot(px + 12000 * math.cos(d), py + 12000 * math.sin(d))], "trunk"))
    # keep a roughly circular city footprint
    cx, cy = rot(size / 2.4, size / 2.4)
    rad = size * 0.32
    return [e for e in out if math.hypot(e[0][0][0] - cx, e[0][0][1] - cy) < rad]


# ---------------------------------------------------------------- render

def render(edges, theme, size_key, w_in, h_in, min_pt, formats, dpi, outdir, name):
    bg, fg = THEMES[theme]
    segs, widths = [], []
    for coords, hw in edges:
        segs.append(coords)
        widths.append(width_pt(hw, w_in, min_pt))
    # draw thin streets first so main roads sit on top at junctions
    order = sorted(range(len(segs)), key=lambda i: widths[i])
    segs = [segs[i] for i in order]
    widths = [widths[i] for i in order]

    xs = [p[0] for s in segs for p in s]
    ys = [p[1] for s in segs for p in s]
    fig = plt.figure(figsize=(w_in, h_in), facecolor=bg)
    ax = fig.add_axes([MARGIN, MARGIN, 1 - 2 * MARGIN, 1 - 2 * MARGIN])
    ax.set_facecolor(bg)
    ax.axis("off")
    ax.set_aspect("equal", adjustable="box")  # no distortion, map centred in the margin box
    ax.set_xlim(min(xs), max(xs))
    ax.set_ylim(min(ys), max(ys))
    ax.add_collection(LineCollection(segs, colors=fg, linewidths=widths,
                                     capstyle="round", joinstyle="round", antialiased=True))

    outdir.mkdir(parents=True, exist_ok=True)
    for ext in formats:
        path = outdir / f"{name}-{theme}-{size_key}.{ext}"
        # No bbox_inches="tight": the file must be exactly the page size.
        fig.savefig(path, facecolor=bg, dpi=dpi)
        print("Saved", path)
    plt.close(fig)


def parse_size(text):
    if text in SIZES:
        return text, SIZES[text]
    m = re.fullmatch(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", text)
    if not m:
        raise argparse.ArgumentTypeError(f"size must be one of {sorted(SIZES)} or WxH inches, e.g. 12x16")
    return text, (float(m.group(1)), float(m.group(2)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--place", default="Delhi, India", help="Place name (full boundary), default Delhi, India")
    src.add_argument("--point", type=float, nargs=2, metavar=("LAT", "LON"), help="Centre point instead of a place")
    src.add_argument("--preview", action="store_true", help="Use a synthetic network, no download (tune the look)")
    ap.add_argument("--dist", type=int, default=9000, help="With --point: half-width of the area in metres")
    ap.add_argument("--name", help="Output file prefix (default: derived from the place)")
    ap.add_argument("--theme", default="blue", choices=sorted(THEMES))
    ap.add_argument("--size", type=parse_size, default="a3", help="a4 | a3 | 18x24 | custom WxH inches")
    ap.add_argument("--dpi", type=int, default=300, help="PNG resolution (300 for print, ~100 for web)")
    ap.add_argument("--min-width", type=float, default=0.25, help="Thinnest line in points (printers drop hairlines)")
    ap.add_argument("--formats", default="pdf,png", help="Comma list of pdf,png,svg. SVG can be hundreds of MB for a big city")
    ap.add_argument("--out", default=str(HERE.parent / "assets"))
    args = ap.parse_args()

    size_key, (w_in, h_in) = args.size if isinstance(args.size, tuple) else parse_size(args.size)
    if args.preview:
        edges, name = synthetic_edges(), args.name or "preview"
    else:
        edges, name = load_edges(args)

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    px = f"{int(w_in * args.dpi)}x{int(h_in * args.dpi)} px"
    print(f"Rendering {w_in} x {h_in} in ({px} PNG at {args.dpi} dpi), theme '{args.theme}' ...")
    render(edges, args.theme, size_key, w_in, h_in, args.min_width, formats, args.dpi, Path(args.out), name)


if __name__ == "__main__":
    main()
