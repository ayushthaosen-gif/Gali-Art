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
import sys
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
CENTRES = {"delhi": (28.6139, 77.2090), "mumbai": (19.0760, 72.8777), "kolkata": (22.5726, 88.3639), "guwahati": (26.1445, 91.7362)}

FONT_URLS = {
    "Jost.ttf": "https://github.com/google/fonts/raw/main/ofl/jost/Jost%5Bwght%5D.ttf",
    "DMMono-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/dmmono/DMMono-Regular.ttf",
}


def load_layout():
    with open(LAYOUT_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def clean_detail(text, limit=40):
    """Detail line as typed, tidied (design 5d): one line, ' - ' becomes ' · ', curly quotes and apostrophes, capped."""
    t = re.sub(r"\s+", " ", text or "").strip()
    t = t.replace(" - ", " \u00b7 ").replace(" \u2013 ", " \u00b7 ").replace(" \u2014 ", " \u00b7 ")
    t = re.sub(r"(^|[\s(\[])\"", "\\1\u201c", t).replace('"', "\u201d")
    t = re.sub(r"(^|[\s(\[])'", "\\1\u2018", t).replace("'", "\u2019")
    return t[:limit].rstrip()


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
    out = []
    for ch in text:
        try:
            out.append(font.load_char(ord(ch), flags=NO_HINT).linearHoriAdvance / 65536.0)
        except RuntimeError:  # glyph missing from this font: keep going with a typical width
            out.append(0.6 * size_pt)
    return out


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
    """Return ([(coords, highway), ...], CRS) in projected metres."""
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

    G = ox.project_graph(G)
    edges = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)
    names = edges["name"] if "name" in edges else [None] * len(edges)
    out = [(list(g.coords), hw, nm) for g, hw, nm in zip(edges.geometry, edges["highway"], names)]
    if args.no_cleanup:
        out = [(c, hw) for c, hw, _ in out]
    else:
        from cleanup import LUTYENS_RADIALS, promote_names
        out, n = promote_names(out, LUTYENS_RADIALS, 2, tier_of)
        print(f"Kept {n:,} Lutyens' Delhi radial segments at tier 2" if n else "")
    print(f"{len(out):,} road segments")
    return out, edges.crs


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
    # Translation preserves the preview's shape and rendering; coordinates are UTM zone 43N.
    return [([(x - cx + 717987, y - cy + 3167131) for x, y in coords], hw)
            for coords, hw in out if math.hypot(coords[0][0] - cx, coords[0][1] - cy) < rad]


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

    if texts.get("detail"):  # optional detail line closes the stack in Jost sentence case after a larger gap (design 5d)
        line("detail", L["detail"], texts["detail"], 1.2, False, False, L["detail"]["above"])
    if texts.get("edition"):  # optional edition number, e.g. "NO. 14 / 100", above the detail line
        line("edition", L["year"], texts["edition"], 1.2, True, False, L["year"]["above"])
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


def heart_path():
    """Unit heart outline for scatter markers (matplotlib rescales custom marker paths itself)."""
    from matplotlib.path import Path
    pts = []
    for i in range(81):
        t = 2 * math.pi * i / 80
        pts.append((16 * math.sin(t) ** 3,
                    13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)))
    return Path(pts, closed=True)


def draw_mark(ax, L, Wp, bg, fg, mark):
    """mark = (x, y, style) in the map's data coordinates. A background-coloured halo keeps it readable over dense streets."""
    x, y, style = mark
    d = L["mark"]["size"] * Wp  # diameter in points
    ax.scatter([x], [y], s=(d * L["mark"]["halo"]) ** 2, c=bg, marker="o", linewidths=0, zorder=10)
    if style == "dot":
        ax.scatter([x], [y], s=d * d, c=fg, marker="o", linewidths=0, zorder=11)
    elif style == "ring":
        ax.scatter([x], [y], s=d * d, facecolors="none", edgecolors=fg, marker="o",
                   linewidths=max(0.8, d * 0.18), zorder=11)
    elif style == "heart":
        ax.scatter([x], [y], s=d * d, c=fg, marker=heart_path(), linewidths=0, zorder=11)


def warn_scripts(*texts):
    """Footer text is placed glyph by glyph, which cannot shape Indic/Arabic scripts (conjuncts, joining)."""
    for t in texts:
        if t and any(ord(c) > 0x24F for c in t):
            print(f"WARNING: '{t}' contains non-Latin characters. This generator cannot shape them "
                  "correctly (e.g. Devanagari conjuncts); set that text in a design tool instead.")


def fmt_edition(text):
    m = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", text)
    return f"NO. {m.group(1)} / {m.group(2)}" if m else text.upper()


def render(edges, L, theme, size_key, w_in, h_in, min_pt, formats, dpi, outdir, name, year, texts, bleed_mm, water=(), mark=None):
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
    if not allx:
        raise ValueError("No renderable road segments remain; check the raster, threshold or max tier")

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
    if water:  # river and lakes: a faint tint of the line colour, under all roads
        from matplotlib.patches import PathPatch
        from matplotlib.path import Path as MPath
        verts, codes = [], []
        for poly in water:
            for ring in [poly.exterior, *poly.interiors]:
                pts = list(ring.coords)
                verts += pts
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), facecolor=mix(bg, fg, L["mix"]["water"]),
                               edgecolor="none", zorder=0.5))
    for z, t in enumerate((5, 4, 3, 2, 1)):
        segs, widths = buckets[t]
        if segs:
            ax.add_collection(LineCollection(segs, colors=minor_c if t == 5 else fg, linewidths=widths,
                                             capstyle="round", joinstyle="round", zorder=z + 1))

    if mark:
        if not (min(allx) <= mark[0] <= max(allx) and min(ally) <= mark[1] <= max(ally)):
            print("WARNING: the marked point is outside the mapped area, so it will not be drawn.")
        draw_mark(ax, L, Wp, bg, fg, mark)

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


def mask_bounds(edges):
    """(minx, miny, maxx, maxy) of the streets that are drawn: exactly the data limits of the poster's map box."""
    xs = [p[0] for coords, hw in edges if tier_of(hw) is not None for p in coords]
    ys = [p[1] for coords, hw in edges if tier_of(hw) is not None for p in coords]
    return min(xs), min(ys), max(xs), max(ys)


def write_georef(edges, crs, L, name, year):
    """Record where the map sits on the earth so the website can place a marker or a crop box from a latitude and longitude.
    Saved to cache/georef/<name>-<year>.json; city_geo.py turns these into a small formula per city for config.js."""
    import json
    minx, miny, maxx, maxy = mask_bounds(edges)
    path = HERE / "cache" / "georef" / f"{name}-{year}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"crs": str(crs), "bounds": [minx, miny, maxx, maxy], "aspect": L["map"]["aspect"]}, indent=1), encoding="utf-8")
    print("Saved", path)


def render_mask(edges, L, outdir, name, year, width_px=1600, crs=None):
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
    if crs is not None:
        write_georef(edges, crs, L, name, year)


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
    src.add_argument("--address", help="Centre the map on this address or place (geocoded, used like --point; needs internet)")
    src.add_argument("--preview", action="store_true", help="Use a synthetic network, no download (tune the look)")
    ap.add_argument("--dist", type=int, default=9000, help="With --point: half-width of the area in metres")
    ap.add_argument("--name", help="Output file prefix (default: derived from the place)")
    ap.add_argument("--city-name", help="Footer title (default: first part of --place)")
    ap.add_argument("--region", help="Footer region line (default: last part of --place, e.g. India)")
    ap.add_argument("--coords", type=float, nargs=2, metavar=("LAT", "LON"), help="Footer coordinates (default: city centre)")
    ap.add_argument("--date", default="", help='Optional personal date line, e.g. "14 FEB 2026" (use DD MON YYYY)')
    ap.add_argument("--edition", default="", help='Optional edition number, e.g. 14/100 prints "NO. 14 / 100"')
    ap.add_argument("--mark", type=float, nargs=2, metavar=("LAT", "LON"), help="Mark a place on the map")
    ap.add_argument("--mark-style", choices=["dot", "ring", "heart"], default="dot", help="Marker shape (default dot)")
    ap.add_argument("--detail", default="", help='Optional detail line under the year, e.g. "21,600 km of streets" (max 40 characters)')
    ap.add_argument("--year", type=int, default=2025, help="Map year shown in the footer (OSM data is current, see README)")
    ap.add_argument("--theme", default="blue", choices=sorted(THEMES))
    ap.add_argument("--size", type=parse_size, default="a3", help="a4 | a3 | 18x24 | custom WxH inches")
    ap.add_argument("--dpi", type=int, default=300, help="PNG resolution (300 for print, ~100 for web)")
    ap.add_argument("--min-width", type=float, default=L["roads"]["min_pt"], help="Thinnest line in points")
    ap.add_argument("--bleed-mm", type=float, default=0.0, help="Bleed per side; background fills it. Printers want 3 (0.125 in = 3.2 mm on 18x24)")
    ap.add_argument("--formats", default="pdf,png", help="Comma list of pdf,png,svg,mask. SVG can be hundreds of MB for a big city. "
                    "mask = white-lines-on-transparent map image for the website (see README)")
    extent_src = ap.add_mutually_exclusive_group()
    extent_src.add_argument("--extent-raster", type=Path, action="append", help="GHSL GeoTIFF for a city extent approximation (repeat for several tiles)")
    extent_src.add_argument("--extent-auto", action="store_true", help="Download/cache GHSL 100 m tiles for a city extent approximation")
    ap.add_argument("--extent-threshold", type=float, default=500, help="Minimum built-up surface per cell (m2)")
    ap.add_argument("--extent-buffer", type=int, default=3, help="Morphological closing iterations in cells")
    ap.add_argument("--extent-min-blob", type=int, default=30, help="Minimum connected built-up blob in cells")
    ap.add_argument("--max-tier", type=int, choices=range(1, 6), help="Keep road tiers up to N (1 major, 5 minor)")
    ap.add_argument("--no-cleanup", action="store_true", help="Skip fragment removal, boundary clip, Lutyens tier promotion and water")
    ap.add_argument("--min-fragment", type=float, default=200, help="Drop disconnected road clusters shorter than this many metres")
    ap.add_argument("--no-water", action="store_true", help="Skip the river/lake tint (needs a boundary download the first time)")
    ap.add_argument("--georef", action="store_true", help="Only record where the map sits on the earth (cache/georef/), without rendering")
    ap.add_argument("--out", default=str(HERE.parent / "assets"))
    args = ap.parse_args()
    extent_requested = args.extent_raster or args.extent_auto
    extent_options = any(arg.startswith("--extent-") for arg in sys.argv[1:])
    if extent_options:
        from fetch_ghsl import epoch_for_year
        try:
            epoch = epoch_for_year(args.year)
        except ValueError as exc:
            ap.error(str(exc))
        if not extent_requested:
            ap.error("Extent settings require --extent-raster or --extent-auto")
        if not math.isfinite(args.extent_threshold) or args.extent_threshold <= 0 or args.extent_buffer < 0 or args.extent_min_blob < 0:
            ap.error("Extent threshold must be positive; buffer and min blob must be nonnegative")

    size_key, (w_in, h_in) = args.size if isinstance(args.size, tuple) else parse_size(args.size)

    if args.address:
        import osmnx as ox
        args.point = tuple(ox.geocode(args.address))
        print(f"Geocoded '{args.address}' -> {args.point[0]:.5f}, {args.point[1]:.5f}")

    place_title = (args.address if args.address else
                   args.place if not args.point and not args.preview else "Delhi, India").split(",")
    city = args.city_name or place_title[0].strip()
    region = args.region if args.region is not None else (place_title[-1].strip() if len(place_title) > 1 else "")
    centre = tuple(args.coords) if args.coords else (args.point if args.point else CENTRES.get(slugify(city)))
    texts = {"city": city, "region": region, "year": args.year, "date": args.date.upper(), "detail": clean_detail(args.detail),
             "edition": fmt_edition(args.edition) if args.edition else "",
             "coords": fmt_coords(*centre) if centre else ""}
    name = args.name or ("preview" if args.preview else slugify(city))
    warn_scripts(city, region, texts["detail"])

    if args.preview:
        edges = synthetic_edges()
        edge_crs = "EPSG:32643"
    else:
        if args.year != 2025 and not extent_requested:
            print(f"NOTE: the road data is current OpenStreetMap. --year {args.year} only changes the label; "
                  "historical maps need archival data.")
        edges, edge_crs = load_edges(args)
        if not centre:
            import osmnx as ox
            texts["coords"] = fmt_coords(*ox.geocode(args.place))

    if extent_requested or args.max_tier is not None:
        from extent import build_mask, filter_edges
        total = len(edges)
        mask = None
        if extent_requested:
            import numpy as np
            points = np.asarray([p for coords, _ in edges for p in coords])
            if not len(points):
                ap.error("No road segments loaded")
            bounds = (*points.min(axis=0), *points.max(axis=0))
            rasters = args.extent_raster
            if args.extent_auto:
                from fetch_ghsl import ensure_ghsl_tiles
                from rasterio.warp import transform_bounds
                bbox = transform_bounds(edge_crs, "EPSG:4326", *bounds, densify_pts=101)
                rasters = ensure_ghsl_tiles(bbox, args.year)
            else:
                print(f"City extent approximation: year {args.year} uses epoch {epoch}; "
                      "ensure the supplied rasters match this epoch.")
            mask = build_mask(rasters, bounds, edge_crs, args.extent_threshold,
                              args.extent_buffer, args.extent_min_blob)
            print("NOTE: city extent approximation: modern roads within the historic built-up area, "
                  "not the historical street pattern.")
        edges = filter_edges(edges, mask, args.max_tier)
        print(f"Kept {len(edges):,} of {total:,} road segments")
        if len(edges) < total * 0.05:
            print("WARNING: fewer than 5% kept; check the raster coverage and threshold.")
        if not edges:
            ap.error("No road segments remain after filtering")

    water = []
    if not args.no_cleanup and not args.preview:
        from cleanup import clip_edges, drop_fragments
        if not args.point:
            from cleanup import load_boundary, load_water
            boundary = load_boundary(args.place, edge_crs, HERE / "cache")
            edges, n = clip_edges(edges, boundary)
            print(f"Clipped {n:,} roads at the boundary")
            if not args.no_water:
                water = load_water(args.place, boundary, edge_crs, HERE / "cache")
                print(f"{len(water):,} water polygons")
        edges, n = drop_fragments(edges, args.min_fragment)
        print(f"Dropped {n:,} segments in fragments under {args.min_fragment:g} m")

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    if not formats or any(f not in {"pdf", "png", "svg", "mask"} for f in formats):
        ap.error("formats must be a comma list of pdf,png,svg,mask")
    print(f"Rendering {w_in} x {h_in} in ({int(w_in * args.dpi)}x{int(h_in * args.dpi)} px PNG at {args.dpi} dpi), "
          f"theme '{args.theme}', year {args.year} ...")
    if args.georef:
        write_georef(edges, edge_crs, L, name, args.year)
        return
    if "mask" in formats:
        render_mask(edges, L, Path(args.out), name, args.year, crs=edge_crs)
        formats = [f for f in formats if f != "mask"]
    if formats:
        mark = None
        if args.mark:
            from pyproj import Transformer
            mx, my = Transformer.from_crs("EPSG:4326", edge_crs, always_xy=True).transform(args.mark[1], args.mark[0])
            mark = (mx, my, args.mark_style)
        render(edges, L, args.theme, size_key, w_in, h_in, args.min_width, formats, args.dpi,
               Path(args.out), name, args.year, texts, args.bleed_mm, water, mark)


if __name__ == "__main__":
    main()
