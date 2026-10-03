#!/usr/bin/env python3
"""Render a city's street network as a minimalist poster (PNG + SVG).

Run locally or in Google Colab: it needs network access to the OpenStreetMap
Overpass API. Do NOT run it in a restricted/CI sandbox.

    pip install -r requirements.txt
    python make_poster.py "Delhi, India" --theme blue --dist 12000

Outputs go to ../assets/<slug>-<theme>.png and .svg
"""
import argparse
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmnx as ox

# Keep in sync with themes in ../config.js
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

# Road class -> line width (points). Major roads are drawn heavier.
WIDTHS = {
    "motorway": 2.2, "trunk": 2.2, "primary": 1.8, "secondary": 1.4,
    "tertiary": 1.0, "unclassified": 0.6, "residential": 0.5,
}


def width_for(highway):
    if isinstance(highway, list):
        highway = highway[0]
    return WIDTHS.get(str(highway).replace("_link", ""), 0.4)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("city", help='Place name, e.g. "Delhi, India"')
    ap.add_argument("--theme", default="blue", choices=sorted(THEMES))
    ap.add_argument("--dist", type=int, default=12000, help="Radius in metres around the city centre")
    ap.add_argument("--size", type=float, nargs=2, default=(12, 16), metavar=("W", "H"), help="Figure size in inches")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "assets"))
    args = ap.parse_args()

    bg, line = THEMES[args.theme]
    print(f"Downloading street network for {args.city} (radius {args.dist} m)...")
    lat, lon = ox.geocode(args.city)
    G = ox.graph_from_point((lat, lon), dist=args.dist, network_type="all", simplify=True)

    widths = [width_for(d.get("highway")) for _, _, d in G.edges(data=True)]
    fig, ax = ox.plot_graph(
        G, node_size=0, edge_color=line, edge_linewidth=widths, bgcolor=bg,
        show=False, close=False, figsize=args.size, padding=0.02,
    )
    fig.patch.set_facecolor(bg)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", args.city.split(",")[0].lower()).strip("-")
    for ext in ("png", "svg"):
        path = out / f"{slug}-{args.theme}.{ext}"
        fig.savefig(path, dpi=args.dpi, facecolor=bg, bbox_inches="tight", pad_inches=0.3)
        print("Saved", path)
    plt.close(fig)


if __name__ == "__main__":
    main()
