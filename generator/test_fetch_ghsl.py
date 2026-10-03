#!/usr/bin/env python3
"""Offline downloader checks: python test_fetch_ghsl.py (mock HTTP, no pytest)."""
import io
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

import fetch_ghsl as ghsl


class Response(io.BytesIO):
    def __init__(self, data, status=200, headers=None):
        super().__init__(data)
        self.status = status
        self.headers = {"Content-Type": "application/zip", "Content-Length": str(len(data))}
        self.headers.update(headers or {})


def zipped_tif(name, bounds):
    with MemoryFile() as mem:
        with mem.open(driver="GTiff", width=20, height=20, count=1, dtype="uint16",
                      crs=ghsl.RASTER_CRS, transform=from_origin(bounds[0], bounds[3], 100, 100)) as dst:
            dst.write(np.full((20, 20), 1101, dtype="uint16"), 1)
        tif = mem.read()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(name, tif)
    return out.getvalue()


def main():
    assert ghsl.epoch_for_year(1970) == 1975
    assert ghsl.epoch_for_year(1973) == 1975
    assert ghsl.epoch_for_year(1995) == 1995
    assert ghsl.epoch_for_year(1997) == 1995
    assert ghsl.epoch_for_year(1998) == 2000
    assert ghsl.epoch_for_year(2025) == 2020
    for year in (1920, 1945, 1969, 1971, 1972):
        try:
            ghsl.epoch_for_year(year)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Unsupported year {year} accepted")
    bbox = (77.2295, 28.6129, 77.2295, 28.6129)
    assert ghsl.select_tiles(bbox) == ["R6_C26"]
    assert ghsl.tile_bounds()["R6_C26"] == (6959000, 3000000, 7959000, 4000000)
    for tile, b in ghsl.tile_bounds().items():
        row, col = [int(s[1:]) for s in tile.split("_")]
        assert b[0] == ghsl.GRID_LEFT + (col - 1) * ghsl.GRID_STEP
        assert b[3] == ghsl.GRID_TOP - (row - 1) * ghsl.GRID_STEP
    lonlat = Transformer.from_crs(ghsl.RASTER_CRS, "EPSG:4326", always_xy=True)
    west, south = lonlat.transform(7958900, 3480000)
    east, north = lonlat.transform(7959100, 3480100)
    assert {"R6_C26", "R6_C27"} <= set(ghsl.select_tiles((west, south, east, north)))
    assert ghsl.covers_bounds([(0, 0, 1, 2), (1, 0, 2, 2)], (0, 0, 2, 2))
    assert not ghsl.covers_bounds([(0, 0, 1, 2), (1.1, 0, 2, 2)], (0, 0, 2, 2))

    x, y = Transformer.from_crs("EPSG:4326", ghsl.RASTER_CRS, always_xy=True).transform(*bbox[:2])
    bounds = (x - 1000, y - 1000, x + 1000, y + 1000)
    name = ghsl.URL_TEMPLATE.format(epoch=1995, tile="R6_C26").rsplit("/", 1)[-1]
    payload = zipped_tif(name.replace(".zip", ".tif"), bounds)
    with tempfile.TemporaryDirectory() as tmp, patch.object(ghsl.time, "sleep") as sleep:
        tmp = Path(tmp)
        with patch.object(ghsl, "CACHE", tmp), patch.object(ghsl, "tile_bounds", return_value={"R6_C26": bounds}):
            with patch.object(ghsl.urllib.request, "urlopen", return_value=Response(payload)) as http:
                paths = ghsl.ensure_ghsl_tiles(bbox, 1995)
                assert http.call_count == 1
            with patch.object(ghsl.urllib.request, "urlopen", side_effect=AssertionError("Network forbidden")):
                assert ghsl.ensure_ghsl_tiles(bbox, 1995) == paths
                paths[0].unlink()
                assert ghsl.ensure_ghsl_tiles(bbox, 1995) == paths  # extraction from cached zip
                paths[0].write_bytes(b"corrupt tif")
                assert ghsl.ensure_ghsl_tiles(bbox, 1995) == paths
            with rasterio.open(paths[0]) as src:
                assert src.read(1).min() == 1101

        path = tmp / "resume.zip"
        path.with_suffix(".zip.part").write_bytes(payload[:100])
        with patch.object(ghsl.urllib.request, "urlopen", return_value=Response(
                payload[100:], 206, {"Content-Range": f"bytes 100-{len(payload)-1}/{len(payload)}"})) as http:
            ghsl.download_zip("https://example.invalid/tile.zip", path)
            assert http.call_args.args[0].get_header("Range") == "bytes=100-"
            assert path.read_bytes() == payload

        path = tmp / "restart.zip"
        path.with_suffix(".zip.part").write_bytes(b"stale partial")
        with patch.object(ghsl.urllib.request, "urlopen", return_value=Response(payload)):
            ghsl.download_zip("https://example.invalid/tile.zip", path)
        assert path.read_bytes() == payload

        class Interrupted(Response):
            def read(self, size=-1):
                if self.tell():
                    raise OSError("connection interrupted")
                return super().read(100)

        with patch.object(ghsl.urllib.request, "urlopen", side_effect=[Interrupted(payload), Response(
                payload[100:], 206, {"Content-Range": f"bytes 100-{len(payload)-1}/{len(payload)}"})]) as http:
            path = tmp / "interrupted.zip"
            ghsl.download_zip("https://example.invalid/tile.zip", path)
            assert http.call_count == 2
            assert http.call_args.args[0].get_header("Range") == "bytes=100-"
            assert path.read_bytes() == payload

        sleep.reset_mock()
        with patch.object(ghsl.urllib.request, "urlopen", side_effect=[
                OSError("timeout"), OSError("timeout"), OSError("timeout"), Response(payload)]) as http:
            ghsl.download_zip("https://example.invalid/tile.zip", tmp / "retry.zip")
            assert http.call_count == 4
            assert [c.args[0] for c in sleep.call_args_list] == [1, 2, 4]

        corrupted = bytearray(payload)
        # Flip a byte inside the stored TIFF, leaving the ZIP headers/directory intact.
        corrupted[30 + len(name.replace(".zip", ".tif")) + 20] ^= 1
        for label, data, headers in (("html", b"<html>Error</html>", {"Content-Type": "text/html"}),
                                     ("fake-zip", b"not a zip", {}),
                                     ("bad-crc", bytes(corrupted), {})):
            with patch.object(ghsl.urllib.request, "urlopen", side_effect=lambda *a, **kw: Response(data, headers=headers)) as http:
                try:
                    ghsl.download_zip("https://example.invalid/tile.zip", tmp / f"{label}.zip")
                except RuntimeError:
                    pass
                else:
                    raise AssertionError("Bad response was accepted")
                assert http.call_count == 4
                assert not (tmp / f"{label}.zip").exists()
    print("GHSL downloader tests passed: epoch/grid, coverage, download, resume, retry, ZIP validation and cache")


if __name__ == "__main__":
    main()
