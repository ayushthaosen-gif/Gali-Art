"""Local poster tool: a web page on your own computer that runs make_poster.py for you.

  python tool.py              # then open http://127.0.0.1:8800
  python tool.py --port 9000

Pick a place (search, a Google/Apple/OpenStreetMap link, or latitude,longitude), choose colours, size and extras, press
Preview for a quick look or Build for the print file. Finished files go to ../print-files/<place>/ and stay listed under
"Recent builds". Nothing here is reachable from other computers: the server only listens on 127.0.0.1.

Needs the same environment as make_poster.py (the generator venv) and internet for places that are not cached yet.
"""
import argparse
import ast
import json
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
UI = HERE / "tool"
OUT = (HERE.parent / "print-files").resolve()
JOBS_FILE = HERE / "tool_jobs.json"
GEOREF = HERE / "cache" / "georef"
UA = "gali-art-local-tool (personal use)"
SIZES = ["a4", "a3", "18x24"]
STYLES = ["dot", "ring", "heart"]


def read_themes():
    """The theme list from make_poster.py itself, so the tool never drifts from the generator (no heavy import)."""
    tree = ast.parse((HERE / "make_poster.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "THEMES":
            return {k: {"bg": v[0], "line": v[1]} for k, v in ast.literal_eval(node.value).items()}
    raise SystemExit("THEMES not found in make_poster.py")


THEMES = read_themes()
lock = threading.Lock()
jobs = []                  # newest last
todo = queue.Queue()


# ---------------------------------------------------------------- places
_last_search = [0.0]


def parse_coords(text):
    """Latitude/longitude from a Google, Apple or OpenStreetMap link, or plain 'lat, lon'. None when there are none."""
    t = unquote(text.strip())
    pats = [r"@(-?\d+\.\d+),(-?\d+\.\d+)", r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
            r"[?&](?:q|ll|query|center|sll|daddr|mlat)=(-?\d+\.\d+)[,&](?:mlon=)?(-?\d+\.\d+)",
            r"#map=\d+/(-?\d+\.\d+)/(-?\d+\.\d+)", r"^\s*(-?\d+(?:\.\d+)?)\s*[,; ]\s*(-?\d+(?:\.\d+)?)\s*$"]
    for p in pats:
        m = re.search(p, t)
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
    return None


def resolve(text):
    """Turn what the user typed into a list of {name, lat, lon, ...}. Links and coordinates give one result, words go to Nominatim."""
    import requests
    text = text.strip()
    if not text:
        return []
    if re.match(r"https?://", text):
        try:
            host = urlparse(text).netloc.lower()
            if "goo.gl" in host or host == "g.co":       # short Google Maps links: follow the redirect to the long one
                text = requests.get(text, timeout=15, allow_redirects=True, headers={"User-Agent": UA}).url
        except Exception:
            pass
    got = parse_coords(text)
    if got:
        return [{"name": f"{got[0]:.5f}, {got[1]:.5f}", "lat": got[0], "lon": got[1], "city": "", "region": "", "kind": "point"}]
    if re.match(r"https?://", text):
        return []
    wait = 1.2 - (time.time() - _last_search[0])      # Nominatim allows one request a second
    if wait > 0:
        time.sleep(wait)
    _last_search[0] = time.time()
    r = requests.get("https://nominatim.openstreetmap.org/search", timeout=20, headers={"User-Agent": UA},
                     params={"q": text, "format": "jsonv2", "limit": 6, "addressdetails": 1})
    r.raise_for_status()
    out = []
    for x in r.json():
        parts = [p.strip() for p in x["display_name"].split(",")]
        out.append({"name": x["display_name"], "lat": float(x["lat"]), "lon": float(x["lon"]), "city": parts[0],
                    "region": parts[-1], "kind": x.get("type", ""), "boundary": x.get("category") == "boundary" or x.get("type") in ("city", "administrative", "town")})
    return out


# ---------------------------------------------------------------- maps already downloaded
POINT_GRAPH = re.compile(r"^(?P<name>.+)-(?P<lat>-?\d+\.\d+)-(?P<lon>-?\d+\.\d+)-(?P<dist>\d+)\.graphml$")


def library():
    """Maps whose road data is already in cache/, so building them needs no download. Read from the cache folder and cities.json."""
    cache = HERE / "cache"
    cities = {c["id"]: c for c in json.loads((HERE / "cities.json").read_text(encoding="utf-8"))["cities"]}
    cities["delhi"] = {"id": "delhi", "name": "Delhi", "place": "Delhi, India", "region": "India", "lat": 28.6139, "lon": 77.2090}
    try:
        results = json.loads((cache / "batch_results.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        results = {}
    out = []
    for f in sorted(cache.glob("*.graphml")):               # square maps: cache name is <name>-<lat>-<lon>-<half-width m>
        m = POINT_GRAPH.match(f.name)
        if not m or m["name"].endswith(("-print", "-preview")):
            continue
        c = cities.get(m["name"])
        title = c["name"] if c else m["name"].replace("-", " ").capitalize()
        dist = int(m["dist"])
        out.append({"label": f"{title}, square {2 * dist / 1000:g} km", "city": title, "region": c["region"] if c else "", "lat": float(m["lat"]),
                    "lon": float(m["lon"]), "mode": "square", "place": "", "halfKm": dist / 1000, "cacheName": m["name"]})
    for c in cities.values():                               # whole-city outlines: cache name is the first part of the place name
        square = c.get("mode") == "square" or str(results.get(c["id"], {}).get("mode", "boundary")).startswith("square")
        if square or not (cache / f"{slug(c['place'].split(',')[0])}.graphml").exists():
            continue
        out.append({"label": f"{c['name']}, whole city", "city": c["name"], "region": c["region"], "lat": c["lat"], "lon": c["lon"],
                    "mode": "boundary", "place": c["place"], "halfKm": 5, "cacheName": ""})
    return sorted(out, key=lambda e: e["label"].lower())


# ---------------------------------------------------------------- jobs
def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "poster"


def num(v, lo, hi, what):
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{what} is not a number")
    if not lo <= f <= hi:
        raise ValueError(f"{what} must be between {lo:g} and {hi:g}")
    return f


def build_command(p, preview):
    """Check the form values and turn them into a make_poster.py command. Raises ValueError with a plain message."""
    city = str(p.get("city", "")).strip()
    if not city:
        raise ValueError("Give the poster a title (the big city name at the bottom).")
    if p.get("theme") not in THEMES:
        raise ValueError("Pick a colour theme.")
    size = str(p.get("size", "a3"))
    if size not in SIZES:
        raise ValueError("Pick a size.")
    lat, lon = num(p.get("lat"), -90, 90, "Latitude"), num(p.get("lon"), -180, 180, "Longitude")
    # make_poster caches square maps under --name, so a map from the library keeps its original name to find its data
    name = slug(str(p.get("cacheName") or city))
    folder = slug(city)
    cmd = [sys.executable, str(HERE / "make_poster.py"), "--city-name", city, "--region", str(p.get("region", "")).strip(),
           "--coords", f"{lat:.4f}", f"{lon:.4f}", "--theme", p["theme"], "--size", size, "--year", str(int(num(p.get("year", 2025), 1900, 2100, "Year")))]
    if p.get("mode") == "boundary":
        place = str(p.get("place", "")).strip()
        if not place:
            raise ValueError("Whole-city maps need the place name from the search.")
        cmd += ["--place", place]
    else:
        dist = num(p.get("halfKm", 5), 0.3, 40, "Half-width (km)") * 1000
        cmd += ["--point", f"{lat:.6f}", f"{lon:.6f}", "--dist", str(int(dist))]
    if str(p.get("mark", "")).strip():
        mlat, mlon = num(p.get("markLat"), -90, 90, "Marker latitude"), num(p.get("markLon"), -180, 180, "Marker longitude")
        style = p.get("markStyle", "dot")
        if style not in STYLES:
            raise ValueError("Pick a marker shape.")
        cmd += ["--mark", f"{mlat:.6f}", f"{mlon:.6f}", "--mark-style", style]
    detail = str(p.get("detail", "")).strip()
    if len(detail) > 40:
        raise ValueError("The detail line can be at most 40 characters.")
    if detail:
        cmd += ["--detail", detail]
    date = str(p.get("date", "")).strip()
    if date:
        cmd += ["--date", date]
    edition = str(p.get("edition", "")).strip()
    if edition:
        cmd += ["--edition", edition]
    if preview:
        outdir = OUT / "previews"
        cmd += ["--dpi", "60", "--formats", "png"]     # same --name as the real build: make_poster caches the road data under it
    else:
        outdir = OUT / folder
        bleed = num(p.get("bleed", 0), 0, 10, "Bleed")
        formats = ["png", "pdf"] + (["mask"] if p.get("mask") else [])
        cmd += ["--dpi", str(int(num(p.get("dpi", 300), 50, 600, "Resolution"))), "--formats", ",".join(formats)]
        if bleed:
            cmd += ["--bleed-mm", f"{bleed:g}"]
    outdir.mkdir(parents=True, exist_ok=True)
    cmd += ["--name", name, "--out", str(outdir)]
    return cmd, outdir, name


def save_jobs():
    keep = [{k: v for k, v in j.items() if k != "log"} | {"log": j["log"][-4000:]} for j in jobs][-60:]
    JOBS_FILE.write_text(json.dumps(keep, indent=1), encoding="utf-8")


def run_job(j):
    j["status"], j["started"] = "running", time.time()
    try:
        cmd, outdir, name = build_command(j["params"], j["preview"])
        # a transparent-map build writes cache/georef/<name>-<year>.json, which the website's marker uses: put back what was there
        saved = {f: f.read_bytes() for f in GEOREF.glob(f"{name}-*.json")}
        proc = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            j["log"] += line
            m = re.match(r"Saved (.+)", line.strip())
            if m:
                path = (HERE / m.group(1)).resolve()
                if OUT in path.parents and path.exists() and "georef" not in path.parts:
                    j["files"].append(path.relative_to(OUT).as_posix())
        proc.wait()
        j["status"] = "done" if proc.returncode == 0 and j["files"] else "failed"
        if j["status"] == "failed":
            tail = j["log"][-600:]
            busy = re.search(r"504|429|timed out|Timeout|ConnectionError|Overpass", j["log"])
            j["error"] = ("The OpenStreetMap server is busy or not answering. Try again in a few minutes. " if busy else "") + tail.strip().splitlines()[-1] if tail.strip() else "make_poster.py stopped without a file."
        for f in GEOREF.glob(f"{name}-*.json"):   # the tool's maps must not change the website's map-position data
            f.unlink()
        for f, data in saved.items():
            f.write_bytes(data)
    except ValueError as exc:
        j["status"], j["error"] = "failed", str(exc)
    except Exception as exc:
        j["status"], j["error"] = "failed", f"{type(exc).__name__}: {exc}"
    j["finished"] = time.time()
    with lock:
        save_jobs()


def worker():
    while True:
        j = todo.get()
        run_job(j)


def add_job(params, preview):
    j = {"id": uuid.uuid4().hex[:8], "created": time.time(), "preview": bool(preview), "params": params,
         "status": "queued", "files": [], "log": "", "error": ""}
    with lock:
        jobs.append(j)
        save_jobs()
    todo.put(j)
    return j


def public(j):
    return {k: j[k] for k in ("id", "created", "preview", "params", "status", "files", "error")} | {"log": j["log"][-1500:]}


# ---------------------------------------------------------------- server
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def local_only(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):     # blocks DNS-rebinding style access
            self.send(403, {"error": "local use only"})
            return False
        return True

    def do_GET(self):
        if not self.local_only():
            return
        path = urlparse(self.path).path
        if path == "/":
            return self.send(200, (UI / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/state":
            with lock:
                return self.send(200, {"themes": THEMES, "sizes": SIZES, "jobs": [public(j) for j in reversed(jobs)][:30]})
        if path == "/api/library":
            return self.send(200, {"maps": library()})
        if path.startswith("/files/"):
            f = (OUT / unquote(path[7:])).resolve()
            if OUT not in f.parents or not f.is_file():
                return self.send(404, {"error": "not found"})
            ctype = {".png": "image/png", ".pdf": "application/pdf"}.get(f.suffix.lower(), "application/octet-stream")
            return self.send(200, f.read_bytes(), ctype)
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if not self.local_only():
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except ValueError:
            return self.send(400, {"error": "bad request"})
        path = urlparse(self.path).path
        if path == "/api/resolve":
            try:
                return self.send(200, {"results": resolve(str(body.get("q", "")))})
            except Exception as exc:
                return self.send(200, {"results": [], "error": f"Search failed ({type(exc).__name__}). Check your internet and try again."})
        if path == "/api/build":
            try:
                build_command(body["params"], bool(body.get("preview")))      # reject bad input before queueing
            except (ValueError, KeyError) as exc:
                return self.send(400, {"error": str(exc)})
            return self.send(200, public(add_job(body["params"], bool(body.get("preview")))))
        self.send(404, {"error": "not found"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8800)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if JOBS_FILE.exists():
        try:
            for j in json.loads(JOBS_FILE.read_text(encoding="utf-8")):
                if j["status"] in ("queued", "running"):
                    j["status"], j["error"] = "failed", "The tool was closed before this finished."
                jobs.append(j)
        except ValueError:
            pass
    threading.Thread(target=worker, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Gali poster tool: http://127.0.0.1:{args.port}   (Ctrl+C to stop)\nFiles go to {OUT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
