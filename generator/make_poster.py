#!/usr/bin/env python3
"""Render a city's street network as a minimalist, print-ready poster (layout 1a).

Centred map, footer with city / region / coordinates / map year. All geometry comes
from ../data/layout.json (fractions of poster width), the same file the website reads,
so the preview and the print file can't drift.

Run locally or in Google Colab: downloading needs access to the OpenStreetMap
Overpass API. Do NOT run it in a restricted/CI sandbox. (--preview needs no network.)

    pip install -r requirements.txt
    python make_poster.py --preview --size a4                    # offline look-and-feel test
    python make_poster.py --place "Delhi, India" --theme blue --size 18x24
    python make_poster.py --point 28.6139 77.2090 --dist 9000 --city-name Delhi --size a3
    python make_poster.py --place "Delhi, India" --size a3 --bleed-mm 3   # file for the printer

Outputs (PDF master + PNG) go to ../assets/<name>-<year>-<theme>-<size>.<ext>.
The downloaded graph is cached in ./cache so changing theme/size/year doesn't re-download.
"""
import argparse
import json
import math
import random
import re
import urllib.request
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.collections import LineCollection
from matplotlib.font_manager import FontProperties

try:  # matplotlib >= 3.10
    from matplotlib.ft2font import LoadFlags
    NO_HINT = LoadFlags.NO_HINTING
except ImportError:  # older
    from matplotlib.ft2font import LOAD_NO_HINTING as NO_HINT

HERE = Path(__file__).resolve().parent
LAYOUT_PATH = HERE.parent / "data" / "layout.json"

# Keep in sync with themes in ../config.js (background, line). Text, rule and major roads use `line`.
THEMES = {
    "blue":       ("#3F6BA8", "#FFFFFF"),
    "dark-gold":  ("#14161A", "#C9A35B"),
    "cream":      ("#F2ECE0", "#1C1C1C"),
    "forest":     ("#23392E", "#E6DFC8"),
    "blush":      ("#EED9D2", "#5A2F2C"),
    "midnight":   ("#0F1B2D", "#D8DEE8"),
    "terracotta": ("#A64E33", "#FBEFE3"),
    "mono":       ("#D9D9D6", "#2B2B2B"),
}

# Poster sizes in inches (width, height). Keep in sync with sizes in ../config.js
SIZES = {"a4": (8.27, 11.69), "a3": (11.69, 16.54), "18x24": (18.0, 24.0)}

# OSM highway tag -> road tier (1 = heaviest). Anything not listed (service, track, footway...) is dropped.
TIERS = {
    "motorway": 1, "trunk": 1, "primary": 2, "secondary": 3, "tertiary": 4,
    "residential": 5, "unclassified": 5, "living_street": 5,
}

# Recognisable centres for the coordinates line (not the boundary centroid).
CENTRES = {"delhi": (28.6139, 77.2090), "mumbai": (19.0760, 72.8777), "kolkata": (22.5726, 88.3639)}

FONT_URLS = {
    "Jost.ttf": "https://github.com/google/fonts/raw/main/ofl/jost/Jost%5Bwght%5D.ttf",
    "DMMono-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/dmmono/DMMono-Regular.ttf",
}


def load_layout():
    with open(LAYOUT_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.split(",")[0].lower()).strip("-") or "city"


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    """Colour a blended toward b by share t, as #RRGGBB."""
    A, B = hex_rgb(a), hex_rgb(b)
    return "#" + "".join(f"{round(x * (1 - t) + y * t):02x}" for x, y in zip(A, B))


def fmt_coords(lat, lon):
    """Decimal degrees, 4 places, hemisphere letter: 28.6139° N, 77.2090° E"""
    return (f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'}, "
            f"{abs(lon):.4f}° {'E' if lon >= 0 else 'W'}")


# ---------------------------------------------------------------- fonts

def get_fonts():
    """Return (sans, mono) FontProperties. Downloads Jost and DM Mono (OFL) once into ./fonts;
    falls back to DejaVu with a warning if that fails."""
    fdir = HERE / "fonts"
    fdir.mkdir(exist_ok=True)
    fps = []
    for fname, fallback in (("Jost.ttf", "DejaVu Sans"), ("DMMono-Regular.ttf", "DejaVu Sans Mono")):
        path = fdir / fname
        if not path.exists():
            try:
                print(f"Downloading font {fname} ...")
                urllib.request.urlretrieve(FONT_URLS[fname], path)
            except Exception as exc:  # offline, blocked, ...
                print(f"WARNING: could not get {fname} ({exc}). Using {fallback}; "
                      f"download it manually into {fdir} for the real look.")
                path.unlink(missing_ok=True)
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            fps.append(FontProperties(fname=str(path)))
        else:
            fps.append(FontProperties(family=fallback))
    return fps[0], fps[1]


def advances(fp, text, size_pt):
    font = font_manager.get_font(font_manager.findfont(fp))
    font.set_size(size_pt, 72)
    return [font.load_char(ord(ch), flags=NO_HINT).linearHoriAdvance / 65536.0 for ch in text]


def tracked_text(fig, fp, text, size_pt, track_em, cx_pt, base_pt, color, fw_pt, fh_pt):
    """Matplotlib has no letter-spacing: place each glyph by advance + tracking, centred with the
    trailing gap removed. cx/base are in points from the figure's left/bottom."""
    adv = advances(fp, text, size_pt)
    gap = track_em * size_pt
    total = sum(adv) + gap * (len(text) - 1)
    x = cx_pt - total / 2
    for ch, a in zip(text, adv):
        if ch != " ":
            fig.text(x / fw_pt, base_pt / fh_pt, ch, fontproperties=fp, fontsize=size_pt,
                     color=color, ha="left", va="baseline")
        x += a + gap


# ---------------------------------------------------------------- data

def load_edges(args):
    """Return [(coords, highway), ...] in a projected CRS (metres)."""
    import osmnx as ox

    ox.settings.timeout = 600
    ox.settings.use_cache = True
    cache = HERE / "cache"
    cache.mkdir(exist_ok=True)

    if args.point:
        key = f"{slugify(args.name or 'point')}-{args.point[0]:.3f}-{args.point[1]:.3f}-{args.dist}"
    else:
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
    return out


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
    cx, cy = rot(size / 2.4, size / 2.4)
    rad = size * 0.32
    return [e for e in out if math.hypot(e[0][0][0] - cx, e[0][0][1] - cy) < rad]


def tier_of(highway):
    if isinstance(highway, list):
        highway = highway[0]
    return TIERS.get(str(highway).replace("_link", ""))


# ---------------------------------------------------------------- render

def footer_lines(L, Wp, Hp, texts):
    """Footer stack laid out bottom-up (mirrors js/poster.js). Units: points from the TOP of the trim box.
    texts: dict city/region/coords/year. Returns (list of line dicts, rule dict)."""
    lines, cursor = [], Hp - L["footer"]["bottom"] * Wp

    def line(key, spec, text, lh, mono, upper, gap_above):
        nonlocal cursor
        s = spec["size"] * Wp
        h = lh * s
        top = cursor - h
        lines.append({"text": text.upper() if upper else text, "size": s, "track": spec["track"],
                      "mono": mono, "base": top + h / 2 + 0.35 * s})
        cursor = top - gap_above * Wp

    if texts.get("date"):  # optional personalised date, e.g. "14 FEB 2026", under the year
        line("date", L.get("date", L["year"]), texts["date"], 1.2, True, False, L.get("date", L["year"])["above"])
    line("year", L["year"], str(texts["year"]), 1.2, True, False, L["year"]["above"])
    if texts.get("coords"):
        line("coords", L["coords"], texts["coords"], 1.2, True, False, L["coords"]["above"])
    if texts.get("region"):
        line("region", L["region"], texts["region"], 1.2, False, True, L["rule"]["below"])
    rh = L["rule"]["h"] * Wp
    rtop = cursor - rh
    rule = {"x": (Wp - L["rule"]["w"] * Wp) / 2, "y": rtop, "w": L["rule"]["w"] * Wp, "h": rh}
    cursor = rtop - L["rule"]["above"] * Wp
    line("city", L["city"], texts["city"], 1.0, False, True, 0)
    return lines, rule


def render(edges, L, theme, size_key, w_in, h_in, min_pt, formats, dpi, outdir, name, year, texts, bleed_mm):
    bg, fg = THEMES[theme]
    minor_c = mix(fg, bg, L["mix"]["minor"])
    Wp, Hp = w_in * 72.0, h_in * 72.0                       # trim size, points
    b = bleed_mm / 25.4 * 72.0                              # bleed, points
    FW, FH = Wp + 2 * b, Hp + 2 * b                         # figure size, points

    # bucket segments by tier; thin streets drawn first so main roads sit on top
    buckets = {t: ([], []) for t in range(1, 6)}
    for coords, hw in edges:
        t = tier_of(hw)
        if t is None:
            continue
        buckets[t][0].append(coords)
        buckets[t][1].append(max(min_pt, L["roads"][f"t{t}"] * Wp))
    allx = [p[0] for t in buckets.values() for s in t[0] for p in s]
    ally = [p[1] for t in buckets.values() for s in t[0] for p in s]

    plt.rcParams["pdf.fonttype"] = 42  # embed fonts as TrueType
    fig = plt.figure(figsize=(FW / 72, FH / 72), facecolor=bg)

    # map axes: 80% W wide, top edge at 12% W, equal aspect, anchored to the top of its box
    mw = L["map"]["width"] * Wp
    mh = mw / L["map"]["aspect"]
    ax = fig.add_axes([(b + (Wp - mw) / 2) / FW, (FH - b - L["map"]["top"] * Wp - mh) / FH, mw / FW, mh / FH])
    ax.set_facecolor(bg)
    ax.axis("off")
    ax.set_aspect("equal", adjustable="box")
    ax.set_anchor("N")
    ax.set_xlim(min(allx), max(allx))
    ax.set_ylim(min(ally), max(ally))
    for z, t in enumerate((5, 4, 3, 2, 1)):
        segs, widths = buckets[t]
        if segs:
            ax.add_collection(LineCollection(segs, colors=minor_c if t == 5 else fg, linewidths=widths,
                                             capstyle="round", joinstyle="round", zorder=z + 1))

    # footer
    sans, mono = get_fonts()
    lines, rule = footer_lines(L, Wp, Hp, texts)
    cx = b + Wp / 2
    for ln in lines:
        tracked_text(fig, mono if ln["mono"] else sans, ln["text"], ln["size"], ln["track"],
                     cx, FH - (b + ln["base"]), fg, FW, FH)
    fig.add_artist(plt.Rectangle(((b + rule["x"]) / FW, (FH - b - rule["y"] - rule["h"]) / FH),
                                 rule["w"] / FW, rule["h"] / FH, transform=fig.transFigure,
                                 facecolor=fg, edgecolor="none"))

    outdir.mkdir(parents=True, exist_ok=True)
    for ext in formats:
        path = outdir / f"{name}-{year}-{theme}-{size_key}.{ext}"
        fig.savefig(path, facecolor=bg, dpi=dpi)  # no bbox_inches="tight": exact page size (+bleed)
        print("Saved", path)
    plt.close(fig)


def render_mask(edges, L, outdir, name, year, width_px=1600):
    """White streets on a transparent background, sized to the map box (layout map.aspect).
    The website recolours this per theme with an alpha mask. Drop it in assets/ and register it in
    config.js under the city's `maps`."""
    plt.rcParams["pdf.fonttype"] = 42
    mw_in = 8.0
    mh_in = mw_in / L["map"]["aspect"]
    poster_w_pt = mw_in * 72.0 / L["map"]["width"]  # width the poster would have if this map were 80% of it
    buckets = {t: ([], []) for t in range(1, 6)}
    for coords, hw in edges:
        t = tier_of(hw)
        if t is not None:
            buckets[t][0].append(coords)
            buckets[t][1].append(max(L["roads"]["min_pt"], L["roads"][f"t{t}"] * poster_w_pt))
    allx = [p[0] for t in buckets.values() for s in t[0] for p in s]
    ally = [p[1] for t in buckets.values() for s in t[0] for p in s]
    fig = plt.figure(figsize=(mw_in, mh_in))
    fig.patch.set_alpha(0)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.patch.set_alpha(0)
    ax.axis("off")
    ax.set_aspect("equal", adjustable="box")
    ax.set_anchor("N")  # same anchoring as the poster's map box
    ax.set_xlim(min(allx), max(allx))
    ax.set_ylim(min(ally), max(ally))
    for z, t in enumerate((5, 4, 3, 2, 1)):
        segs, widths = buckets[t]
        if segs:
            ax.add_collection(LineCollection(segs, colors="#FFFFFF", linewidths=widths,
                                             capstyle="round", joinstyle="round", zorder=z + 1))
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{name}-{year}-lines.png"
    fig.savefig(path, dpi=width_px / mw_in, transparent=True)
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
    L = load_layout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--place", default="Delhi, India", help="Place name (full boundary), default Delhi, India")
    src.add_argument("--point", type=float, nargs=2, metavar=("LAT", "LON"), help="Centre point instead of a place")
    src.add_argument("--preview", action="store_true", help="Use a synthetic network, no download (tune the look)")
    ap.add_argument("--dist", type=int, default=9000, help="With --point: half-width of the area in metres")
    ap.add_argument("--name", help="Output file prefix (default: derived from the place)")
    ap.add_argument("--city-name", help="Footer title (default: first part of --place)")
    ap.add_argument("--region", help="Footer region line (default: last part of --place, e.g. India)")
    ap.add_argument("--coords", type=float, nargs=2, metavar=("LAT", "LON"), help="Footer coordinates (default: city centre)")
    ap.add_argument("--date", default="", help='Optional personal date line, e.g. "14 FEB 2026" (use DD MON YYYY)')
    ap.add_argument("--year", type=int, default=2025, help="Map year shown in the footer (OSM data is current, see README)")
    ap.add_argument("--theme", default="blue", choices=sorted(THEMES))
    ap.add_argument("--size", type=parse_size, default="a3", help="a4 | a3 | 18x24 | custom WxH inches")
    ap.add_argument("--dpi", type=int, default=300, help="PNG resolution (300 for print, ~100 for web)")
    ap.add_argument("--min-width", type=float, default=L["roads"]["min_pt"], help="Thinnest line in points")
    ap.add_argument("--bleed-mm", type=float, default=0.0, help="Bleed per side; background fills it. Printers want 3 (0.125 in = 3.2 mm on 18x24)")
    ap.add_argument("--formats", default="pdf,png", help="Comma list of pdf,png,svg,mask. SVG can be hundreds of MB for a big city. "
                    "mask = white-lines-on-transparent map image for the website (see README)")
    ap.add_argument("--out", default=str(HERE.parent / "assets"))
    args = ap.parse_args()

    size_key, (w_in, h_in) = args.size if isinstance(args.size, tuple) else parse_size(args.size)

    place_title = (args.place if not args.point and not args.preview else "Delhi, India").split(",")
    city = args.city_name or place_title[0].strip()
    region = args.region if args.region is not None else (place_title[-1].strip() if len(place_title) > 1 else "")
    centre = tuple(args.coords) if args.coords else (args.point if args.point else CENTRES.get(slugify(city)))
    texts = {"city": city, "region": region, "year": args.year, "date": args.date.upper(),
             "coords": fmt_coords(*centre) if centre else ""}
    name = args.name or ("preview" if args.preview else slugify(city))

    if args.preview:
        edges = synthetic_edges()
    else:
        if args.year != 2025:
            print(f"NOTE: the road data is current OpenStreetMap. --year {args.year} only changes the label; "
                  "historical maps need archival data.")
        edges = load_edges(args)
        if not centre:
            import osmnx as ox
            texts["coords"] = fmt_coords(*ox.geocode(args.place))

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    print(f"Rendering {w_in} x {h_in} in ({int(w_in * args.dpi)}x{int(h_in * args.dpi)} px PNG at {args.dpi} dpi), "
          f"theme '{args.theme}', year {args.year} ...")
    if "mask" in formats:
        render_mask(edges, L, Path(args.out), name, args.year)
        formats = [f for f in formats if f != "mask"]
    if formats:
        render(edges, L, args.theme, size_key, w_in, h_in, args.min_width, formats, args.dpi,
               Path(args.out), name, args.year, texts, args.bleed_mm)


if __name__ == "__main__":
    main()
