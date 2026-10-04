"""Compute the optional detail-line facts for config.js `cities[].facts` from the cached OSM data.

  python city_facts.py              # writes city_facts.json (read by batch_masks.py --write-config) for every cached city

streetsKm: total length of the drawn street network (tiers 1-5, each street counted once, not once per direction),
rounded to 100 km (10 km under 1,000). areaKm2: city-boundary area, rounded to 10 km2, only for cities drawn
with their boundary. Both describe the 2025 map. Needs the graphs cached by make_poster.py / batch_masks.py.
"""
import json
import warnings
from pathlib import Path

import geopandas as gpd
import osmnx as ox

from cleanup import _slug
from make_poster import slugify, tier_of

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def round_to(x, step):
    return int(round(x / step) * step)


def streets_km(graph_path):
    G = ox.project_graph(ox.load_graphml(graph_path))
    seen, km = set(), 0.0
    for u, v, _k, d in G.edges(keys=True, data=True):
        if tier_of(d.get("highway")) is None:
            continue
        key = (min(u, v), max(u, v), round(float(d.get("length", 0)), 1))  # two-way streets appear as u->v and v->u
        if key in seen:
            continue
        seen.add(key)
        km += float(d.get("length", 0)) / 1000
    return km


def main():
    cities = json.loads((HERE / "cities.json").read_text(encoding="utf-8"))["cities"]
    out = {"delhi": {"place": "Delhi, India"}}
    for c in cities:
        out[c["id"]] = c
    result = {}
    for cid, c in out.items():
        graph = next(iter(sorted(CACHE.glob(f"{slugify(c['place'])}.graphml"))), None) if c.get("place") else None
        if graph is None:
            graph = next(iter(sorted(CACHE.glob(f"{cid}-*.graphml"))), None)
        if graph is None:
            continue
        km = streets_km(graph)
        facts = {"streetsKm": round_to(km, 100 if km >= 1000 else 10)}
        boundary = next(iter(CACHE.glob(f"{_slug(c['place'])}-boundary.geojson")), None) if c.get("place") else None
        if boundary and graph.stem == slugify(c["place"]) and c.get("mode") != "square":
            g = gpd.read_file(boundary)
            facts["areaKm2"] = round_to(g.to_crs(g.estimate_utm_crs()).area.iloc[0] / 1e6, 10)
        result[cid] = facts
    (HERE / "city_facts.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
