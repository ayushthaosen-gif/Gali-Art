"""Modern roads within a GHSL built-up extent (an approximation, not historical roads)."""
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds
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
    if threshold <= 0 or buffer_cells < 0 or min_blob_cells < 0:
        raise ValueError("threshold must be positive; buffer and min blob must be nonnegative")
    with rasterio.open(raster_path) as src:
        bounds = transform_bounds(edge_crs, src.crs, *bounds_xy, densify_pts=21)
        window = from_bounds(*bounds, transform=src.transform)
        left, top = np.floor(window.col_off), np.floor(window.row_off)
        right = np.ceil(window.col_off + window.width)
        bottom = np.ceil(window.row_off + window.height)
        left, top = max(0, left), max(0, top)
        right, bottom = min(src.width, right), min(src.height, bottom)
        if right <= left or bottom <= top:
            return ExtentMask(np.zeros((0, 0), dtype=bool), src.transform, edge_crs, src.crs)
        window = Window(left, top, right - left, bottom - top)
        values = src.read(1, window=window, masked=True).filled(0)
        cells = values >= threshold
        if buffer_cells:
            cells = ndimage.binary_closing(cells, iterations=buffer_cells)
        cells = ndimage.binary_fill_holes(cells)
        if min_blob_cells:
            labels, _ = ndimage.label(cells)
            sizes = np.bincount(labels.ravel())
            keep = sizes >= min_blob_cells
            keep[0] = False
            cells = keep[labels]
        return ExtentMask(cells, src.window_transform(window), edge_crs, src.crs)


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
