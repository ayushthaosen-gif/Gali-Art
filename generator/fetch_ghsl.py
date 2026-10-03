"""Cached GHSL downloads for city extent approximations, not historical street maps."""
import argparse
import http.client
import json
import math
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import rasterio
from rasterio.warp import transform_bounds

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "ghsl"
# Verified 2026-10-03 against the official download page, its shapefile index,
# GHSL Data Package 2023, and JRC directory/HEAD/range GET responses for R6_C26.
# https://human-settlement.emergency.copernicus.eu/download.php
# https://human-settlement.emergency.copernicus.eu/download/GHSL_data_54009_shapefile.zip
RELEASE = "R2023A"
RASTER_CRS = "ESRI:54009"
CELL_METRES = 100
GRID_LEFT, GRID_TOP, GRID_STEP = -18041000, 9000000, 1000000
TILE_INDEX = HERE / "ghsl_tiles.json"  # rectangles derived from the official index DBF
URL_TEMPLATE = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_S_GLOBE_R2023A/"
    "GHS_BUILT_S_E{epoch}_GLOBE_R2023A_54009_100/V1-0/tiles/"
    "GHS_BUILT_S_E{epoch}_GLOBE_R2023A_54009_100_V1_0_{tile}.zip"
)
EPOCHS = tuple(range(1975, 2021, 5))


def epoch_for_year(year):
    """Nearest supported epoch; 1970 is an explicit 1975 proxy, ties use the earlier epoch."""
    if year < 1973 and year != 1970:
        raise ValueError("GHSL city extent cannot represent this year: use years >=1973, or "
                         "1970 with the explicitly disclosed 1975 proxy; 1920/1945 need archival data")
    return min(EPOCHS, key=lambda epoch: (abs(epoch - year), epoch))


def tile_bounds():
    with open(TILE_INDEX, encoding="utf-8") as fh:
        return {row[0]: tuple(row[1:]) for row in json.load(fh)["tiles"]}


def projected_bounds(bbox_lonlat):
    west, south, east, north = bbox_lonlat
    if not all(math.isfinite(v) for v in bbox_lonlat) or not (
            -180 <= west <= east <= 180 and -90 <= south <= north <= 90):
        raise ValueError("bbox must be west,south,east,north; split antimeridian-crossing areas")
    return transform_bounds("EPSG:4326", RASTER_CRS, *bbox_lonlat, densify_pts=101)


def select_tiles(bbox_lonlat):
    left, bottom, right, top = projected_bounds(bbox_lonlat)
    # The official land index excludes ocean-only cells and clips the outer columns.
    return [tile for tile, b in tile_bounds().items()
            if b[0] <= right and b[2] >= left and b[1] <= top and b[3] >= bottom]


def valid_zip(path):
    try:
        with zipfile.ZipFile(path) as z:
            return z.testzip() is None and any(n.lower().endswith(".tif") for n in z.namelist())
    except (OSError, zipfile.BadZipFile, EOFError):
        return False


def download_zip(url, path):
    """Four attempts, resumable partial files, CRC validation and atomic cache promotion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and valid_zip(path):
        print(f"Using cached {path.name}")
        return
    part = path.with_suffix(".zip.part")
    for attempt in range(4):
        offset = part.stat().st_size if part.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status not in (200, 206):
                    raise ValueError(f"Unexpected HTTP status {response.status}")
                if response.status == 206:
                    content_range = response.headers.get("Content-Range", "")
                    if not content_range.startswith(f"bytes {offset}-"):
                        part.unlink(missing_ok=True)
                        raise ValueError("Server returned the wrong resume offset")
                else:
                    offset = 0  # a server may ignore Range: safely restart instead of appending
                if "html" in response.headers.get("Content-Type", "").lower():
                    part.unlink(missing_ok=True)
                    raise ValueError("GHSL returned HTML instead of a ZIP")
                length = response.headers.get("Content-Length")
                total = offset + int(length) if length else None
                done, last = offset, 0.0
                with open(part, "ab" if offset else "wb") as fh:
                    while chunk := response.read(1024 * 1024):
                        fh.write(chunk)
                        done += len(chunk)
                        if time.monotonic() - last >= 1:
                            progress = f"{100 * done / total:.0f}%" if total else f"{done / 1e6:.1f} MB"
                            print(f"\rDownloading {path.name}: {progress}", end="", flush=True)
                            last = time.monotonic()
                print()
                if total is not None and done != total:
                    raise OSError(f"Incomplete download ({done}/{total} bytes)")
            if not valid_zip(part):
                part.unlink(missing_ok=True)
                raise ValueError("GHSL download is not a valid TIFF ZIP (signature/CRC failed)")
            part.replace(path)
            return
        except (OSError, ValueError, http.client.HTTPException) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 416:
                part.unlink(missing_ok=True)
            if attempt == 3:
                raise RuntimeError(f"GHSL download failed after 4 tries: {url}: {exc}") from exc
            delay = 2 ** attempt
            print(f"\nRetry {attempt + 2}/4 in {delay}s: {exc}")
            time.sleep(delay)


def verify_tile(path, expected_bounds):
    with rasterio.open(path) as src:
        if src.crs != rasterio.crs.CRS.from_string(RASTER_CRS) or src.res != (CELL_METRES, CELL_METRES):
            raise ValueError(f"{path.name}: expected Mollweide GHSL 100 m raster")
        if any(abs(a - b) > CELL_METRES for a, b in zip(src.bounds, expected_bounds)):
            raise ValueError(f"{path.name}: raster bounds do not match the official tile index")
        src.read(1, window=rasterio.windows.Window(src.width // 2, src.height // 2, 1, 1))
        return tuple(src.bounds)


def covers_bounds(rectangles, bounds):
    left, bottom, right, top = bounds
    cuts = sorted({left, right} | {v for b in rectangles for v in (b[0], b[2]) if left < v < right})
    midpoints = [(a + b) / 2 for a, b in zip(cuts, cuts[1:])] or [left]
    for x in midpoints:
        intervals = sorted((b[1], b[3]) for b in rectangles if b[0] <= x <= b[2])
        covered = bottom
        for lo, hi in intervals:
            if lo > covered:
                break
            covered = max(covered, hi)
        if covered < top or not intervals:
            return False
    return True


def ensure_ghsl_tiles(bbox_lonlat, year):
    epoch = epoch_for_year(year)
    print(f"City extent approximation: year {year} uses GHSL epoch {epoch}; modern roads, "
          "not the historical street pattern.")
    tiles = select_tiles(bbox_lonlat)
    index = tile_bounds()
    bounds = projected_bounds(bbox_lonlat)
    if not tiles or not covers_bounds([index[t] for t in tiles], bounds):
        raise ValueError("The official GHSL land tiles do not cover the whole requested bbox")
    paths, coverage = [], []
    for tile in tiles:
        url = URL_TEMPLATE.format(epoch=epoch, tile=tile)
        archive = CACHE / url.rsplit("/", 1)[-1]
        tif = archive.with_suffix(".tif")
        if tif.exists():
            try:
                coverage.append(verify_tile(tif, index[tile]))
                paths.append(tif)
                print(f"Using cached {tif.name}")
                continue
            except (ValueError, rasterio.errors.RasterioError):
                print(f"Rebuilding invalid cached {tif.name}")
        download_zip(url, archive)
        temp = tif.with_suffix(".tif.part")
        try:
            with zipfile.ZipFile(archive) as z:
                matches = [n for n in z.namelist() if Path(n).name == tif.name]
                if len(matches) != 1:
                    raise ValueError(f"{archive.name}: expected exactly one {tif.name}")
                with z.open(matches[0]) as source, open(temp, "wb") as dest:
                    shutil.copyfileobj(source, dest)
            coverage.append(verify_tile(temp, index[tile]))
            temp.replace(tif)
        finally:
            temp.unlink(missing_ok=True)
        paths.append(tif)
    if not covers_bounds(coverage, bounds):
        raise ValueError("Downloaded GHSL rasters do not cover the requested bbox")
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bbox", type=float, nargs=4, required=True, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    ap.add_argument("--year", type=int, required=True)
    args = ap.parse_args()
    for path in ensure_ghsl_tiles(args.bbox, args.year):
        print(path)
