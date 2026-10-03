"""Modern roads within a GHSL built-up extent (an approximation, not historical roads)."""
from contextlib import ExitStack
import math
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds
from rasterio.merge import merge
from scipy import ndimage


class ExtentMask:
    def __init__(self, cells, transform, edge_crs, raster_crs):
        self.cells = cells
        self.inverse = ~transform
        self.transformer = Transformer.from_crs(edge_crs, raster_crs, always_xy=True)

    def contains(self, x, y):
        x, y = np.broadcast_arrays(x, y)
        rx, ry = self.transformer.transform(x, y)
        col, row = self.inverse * (np.asarray(rx), np.asarray(ry))
        height, width = self.cells.shape
        valid = (np.isfinite(col) & np.isfinite(row) &
                 (col >= 0) & (row >= 0) & (col < width) & (row < height))
        inside = np.zeros(x.shape, dtype=bool)
        inside[valid] = self.cells[np.floor(row[valid]).astype(int),
                                   np.floor(col[valid]).astype(int)]
        return inside


def build_mask(raster_path, bounds_xy, edge_crs, threshold, buffer_cells, min_blob_cells):
    """Read the road bounds only, threshold built-up surface, and clean the extent."""
    if not math.isfinite(threshold) or threshold <= 0 or buffer_cells < 0 or min_blob_cells < 0:
        raise ValueError("threshold must be positive; buffer and min blob must be nonnegative")
    paths = [raster_path] if isinstance(raster_path, (str, Path)) else list(raster_path)
    if not paths:
        raise ValueError("At least one extent raster is required")
    with ExitStack() as stack:
        sources = [stack.enter_context(rasterio.open(path)) for path in paths]
        src = sources[0]
        if any(s.crs != src.crs or s.res != src.res for s in sources):
            raise ValueError("Extent rasters must have the same CRS and cell size")
        if any(s.transform.b or s.transform.d or s.transform.a <= 0 or s.transform.e >= 0
               for s in sources):
            raise ValueError("Extent rasters must be north-up")
        for s in sources:
            col, row = (~src.transform) * (s.transform.c, s.transform.f)
            if not np.allclose([col, row], np.round([col, row]), rtol=0, atol=1e-6):
                raise ValueError("Extent rasters must share an aligned cell grid")
        bounds = transform_bounds(edge_crs, src.crs, *bounds_xy, densify_pts=21)
        coverage = (min(s.bounds.left for s in sources), min(s.bounds.bottom for s in sources),
                    max(s.bounds.right for s in sources), max(s.bounds.top for s in sources))
        bounds = (max(bounds[0], coverage[0]), max(bounds[1], coverage[1]),
                  min(bounds[2], coverage[2]), min(bounds[3], coverage[3]))
        if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
            return ExtentMask(np.zeros((0, 0), dtype=bool), src.transform, edge_crs, src.crs)
        window = from_bounds(*bounds, transform=src.transform)
        left, top = np.floor(window.col_off), np.floor(window.row_off)
        right = np.ceil(window.col_off + window.width)
        bottom = np.ceil(window.row_off + window.height)
        window = Window(left, top, right - left, bottom - top)
        transform = src.window_transform(window)
        if len(sources) == 1:
            values = src.read(1, window=window, masked=True).filled(0)
        else:
            # Merge only the requested window; cleanup then crosses tile seams.
            bounds = rasterio.windows.bounds(window, src.transform)
            values, transform = merge(sources, bounds=bounds, nodata=0, indexes=[1])
            values = values[0]
        cells = values >= threshold
        if buffer_cells:
            padded = np.pad(cells, buffer_cells, mode="edge")
            closed = ndimage.binary_closing(padded, iterations=buffer_cells)
            cells = closed[buffer_cells:-buffer_cells, buffer_cells:-buffer_cells]
        cells = ndimage.binary_fill_holes(cells)
        if min_blob_cells:
            labels, _ = ndimage.label(cells)
            sizes = np.bincount(labels.ravel())
            keep = sizes >= min_blob_cells
            keep[0] = False
            cells = keep[labels]
        return ExtentMask(cells, transform, edge_crs, src.crs)


def filter_edges(edges, mask, max_tier=None):
    """Keep middle vertices inside the extent, with one vectorised raster lookup."""
    from make_poster import tier_of

    if not edges:
        return []
    points = np.asarray([coords[len(coords) // 2] for coords, _ in edges])
    keep = mask.contains(points[:, 0], points[:, 1]) if mask is not None else np.ones(len(edges), dtype=bool)
    if max_tier is not None:
        tiers = np.asarray([tier_of(hw) or 6 for _, hw in edges])
        keep &= tiers <= max_tier
    return [edges[i] for i in np.flatnonzero(keep)]
