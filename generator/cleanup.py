"""Poster clean-up steps applied to the road list ([(coords, highway), ...] in projected metres).

- drop_fragments: remove tiny disconnected road clusters (default < 200 m total)
- clip_edges: clip roads to the city boundary polygon
- promote_names: keep named roads (e.g. Lutyens' Delhi radials) at least at a given tier
- load_boundary / load_water: OSM polygons, cached as GeoJSON in generator/cache/
"""
import math
from collections import defaultdict
from pathlib import Path

# Lutyens' Delhi radial and ceremonial roads. Matched by OSM `name` (case-insensitive substring).
LUTYENS_RADIALS = [
    "Kartavya Path", "Rajpath", "Janpath", "Akbar Road", "Ashoka Road", "Rafi Marg", "Sansad Marg",
    "Tolstoy Marg", "Kasturba Gandhi Marg", "Barakhamba Road", "Tughlak Road", "Prithviraj Road",
    "Shahjahan Road", "Teen Murti Marg", "Sardar Patel Marg", "Kushak Road", "Mother Teresa Crescent",
    "Gurudwara Rakab Ganj Road", "Parliament Street", "Bhagwan Das Road", "Copernicus Marg",
    "Man Singh Road", "Dr. Rajendra Prasad Road", "Krishna Menon Marg", "Aurangzeb Road",
    "Safdarjung Road", "Willingdon Crescent", "Vijay Chowk",
]


def _key(pt):
    return (round(pt[0], 1), round(pt[1], 1))


def _length(coords):
    return sum(math.dist(a, b) for a, b in zip(coords, coords[1:]))


def drop_fragments(edges, min_length_m=200.0):
    """Remove connected components whose total road length is below min_length_m."""
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for coords, _ in edges:
        ra, rb = find(_key(coords[0])), find(_key(coords[-1]))
        if ra != rb:
            parent[ra] = rb
    total = defaultdict(float)
    for coords, _ in edges:
        total[find(_key(coords[0]))] += _length(coords)
    kept = [e for e in edges if total[find(_key(e[0][0]))] >= min_length_m]
    return kept, len(edges) - len(kept)


def clip_edges(edges, boundary):
    """Clip each road to the boundary polygon (projected CRS). Returns (edges, number clipped or dropped)."""
    from shapely import prepared
    from shapely.geometry import LineString
    prep = prepared.prep(boundary)
    out, changed = [], 0
    for coords, hw in edges:
        line = LineString(coords)
        if prep.contains(line):
            out.append((coords, hw))
            continue
        changed += 1
        part = line.intersection(boundary)
        for g in getattr(part, "geoms", [part]):
            if g.geom_type == "LineString" and not g.is_empty and g.length > 0:
                out.append((list(g.coords), hw))
    return out, changed


def promote_names(edges_with_names, names, top_tier, tier_of, promote_to="primary"):
    """edges_with_names: [(coords, highway, name)]. Roads whose name matches and whose tier is below
    top_tier get highway=promote_to. Returns ([(coords, highway)], number promoted)."""
    needles = [n.lower() for n in names]
    out, n = [], 0
    for coords, hw, name in edges_with_names:
        label = " ".join(name).lower() if isinstance(name, list) else str(name or "").lower()
        t = tier_of(hw)
        if t is not None and t > top_tier and any(x in label for x in needles):
            hw, n = promote_to, n + 1
        out.append((coords, hw))
    return out, n


def load_boundary(place, crs, cache):
    """City boundary polygon in `crs`, cached as GeoJSON."""
    import geopandas as gpd
    import osmnx as ox
    path = cache / f"{_slug(place)}-boundary.geojson"
    if path.exists():
        gdf = gpd.read_file(path)
    else:
        gdf = ox.geocode_to_gdf(place)[["geometry"]]
        gdf.to_file(path, driver="GeoJSON")
    return gdf.to_crs(crs).geometry.union_all()


def load_water(place, boundary, crs, cache):
    """Water polygons (rivers, lakes) inside the boundary, as a list of shapely polygons in `crs`."""
    import geopandas as gpd
    import osmnx as ox
    path = cache / f"{_slug(place)}-water.geojson"
    if path.exists():
        gdf = gpd.read_file(path)
    else:
        area = gpd.GeoSeries([boundary], crs=crs).to_crs(4326).iloc[0]
        tags = {"natural": "water", "waterway": "riverbank"}
        gdf = ox.features_from_polygon(area, tags)
        gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])][["geometry"]]
        gdf.to_file(path, driver="GeoJSON")
    water = gdf.to_crs(crs).geometry.union_all().intersection(boundary)
    return [g for g in getattr(water, "geoms", [water]) if g.geom_type == "Polygon" and not g.is_empty]


def _slug(text):
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")
