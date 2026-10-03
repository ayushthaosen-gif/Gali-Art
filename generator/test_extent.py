#!/usr/bin/env python3
"""Offline regression checks: python test_extent.py (no pytest or downloads)."""
import runpy
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import rasterio
from matplotlib.font_manager import FontProperties
from pyproj import Transformer
from rasterio.transform import from_origin

from extent import build_mask, filter_edges
from make_poster import synthetic_edges, tier_of


def main():
    edges = synthetic_edges()
    crs = "EPSG:32643"
    points = np.asarray([p for coords, _ in edges for p in coords])
    bounds = (*points.min(axis=0), *points.max(axis=0))
    transform = from_origin(77.2295 - 0.16, 28.6129 + 0.16, 0.001, 0.001)
    rows, cols = np.indices((320, 320))
    lon, lat = transform * (cols + 0.5, rows + 0.5)
    project = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    x, y = project.transform(lon, lat)
    cx, cy = project.transform(77.2295, 28.6129)
    distance = np.hypot(x - cx, y - cy)
    counts = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for year, radius in ((1975, 2500), (1995, 5500)):
            raster = tmp / f"built-{year}.tif"
            cells = distance <= radius
            values = np.where(cells, 1000, 0).astype("uint16")
            values[0, 0] = 65535
            with rasterio.open(raster, "w", driver="GTiff", height=320, width=320,
                               count=1, dtype="uint16", crs="EPSG:4326",
                               transform=transform, nodata=65535) as dst:
                dst.write(values, 1)
            mask = build_mask(raster, bounds, crs, 500, 3, 30)
            kept = filter_edges(edges, mask)
            counts.append(len(kept))
            middle = np.asarray([coords[len(coords) // 2] for coords, _ in kept])
            assert len(kept) > 0
            assert mask.contains(middle[:, 0], middle[:, 1]).all()
            mlon, mlat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform(
                middle[:, 0], middle[:, 1])
            mcol, mrow = (~transform) * (mlon, mlat)
            assert cells[np.floor(mrow).astype(int), np.floor(mcol).astype(int)].all()
            # Cell-centre rasterisation allows half a cell diagonal at the disc boundary.
            assert (np.hypot(middle[:, 0] - cx, middle[:, 1] - cy) <= radius + 80).all()
            major = filter_edges(edges, mask, max_tier=2)
            assert len(major) < len(kept)
            assert all(tier_of(hw) <= 2 for _, hw in major)
            assert not mask.contains(np.array([cx + 100000]), np.array([cy])).any()
            empty = build_mask(raster, (cx + 100000, cy, cx + 101000, cy + 1000),
                               crs, 500, 3, 30)
            assert not empty.contains(np.array([cx]), np.array([cy])).any()
            assert not build_mask(raster, bounds, crs, 2000, 0, 0).cells.any()

        assert counts[0] < counts[1], counts
        # Execute the actual CLI, replacing font fetching so this is offline on a fresh checkout.
        script = Path(__file__).with_name("make_poster.py")
        argv = [str(script), "--preview", "--extent-raster", str(raster), "--year", "1995",
                "--size", "a4", "--dpi", "40", "--formats", "pdf,png,mask", "--out", str(tmp)]
        fonts = (FontProperties(family="DejaVu Sans"), FontProperties(family="DejaVu Sans Mono"))
        with patch.object(sys, "argv", argv), patch("urllib.request.urlretrieve",
                                                    side_effect=AssertionError("Network forbidden")):
            namespace = runpy.run_path(str(script))
            namespace["main"].__globals__["get_fonts"] = lambda: fonts
            namespace["main"]()
        for name in ("preview-1995-blue-a4.pdf", "preview-1995-blue-a4.png",
                     "preview-1995-lines.png"):
            assert (tmp / name).stat().st_size > 0, name
        import matplotlib.image as mpimg
        image = mpimg.imread(tmp / "preview-1995-lines.png")
        assert image.shape[2] == 4
        assert (image[:, :, 3] == 0).any() and (image[:, :, 3] > 0).any()
        assert np.all(image[:, :, :3][image[:, :, 3] > 0] == 1)
    print(f"Extent tests passed: smaller year {counts[0]:,}, larger year {counts[1]:,} segments")


if __name__ == "__main__":
    main()
