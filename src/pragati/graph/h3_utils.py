"""H3 discrete global grid spatial utilities for PRAGATI."""

from typing import Dict, List, Tuple
import h3
import numpy as np


def create_hex_grid(
    center_lat: float, center_lon: float, radius_cells: int, resolution: int
) -> List[str]:
    """Generate a sorted deterministic list of H3 cells around a center coordinate.

    Args:
        center_lat: Latitude of center in decimal degrees.
        center_lon: Longitude of center in decimal degrees.
        radius_cells: Grid disk radius in cells (k-ring radius).
        resolution: H3 resolution level (0 to 15).

    Returns:
        List[str]: Deterministically sorted list of H3 cell index strings.
    """
    center_cell = h3.latlng_to_cell(center_lat, center_lon, resolution)
    cells_set = h3.grid_disk(center_cell, radius_cells)
    return sorted(list(cells_set))


def get_neighbors(cell: str, k: int = 1) -> List[str]:
    """Retrieve immediate or k-step neighbors of an H3 cell, excluding the input cell itself.

    Args:
        cell: Origin H3 index string.
        k: Neighbor ring distance (default 1).

    Returns:
        List[str]: Deterministically sorted list of neighboring H3 cell index strings.
    """
    cells = set(h3.grid_disk(cell, k))
    cells.discard(cell)
    return sorted(list(cells))


def cell_to_latlon(cell: str) -> Tuple[float, float]:
    """Get the centroid coordinates (latitude, longitude) of an H3 cell.

    Args:
        cell: H3 index string.

    Returns:
        Tuple[float, float]: (latitude, longitude) in decimal degrees.
    """
    lat, lon = h3.cell_to_latlng(cell)
    return float(lat), float(lon)


def cell_area_m2(cell: str) -> float:
    """Compute the approximate surface area of an H3 cell in square metres.

    Args:
        cell: H3 index string.

    Returns:
        float: Cell area in m^2.
    """
    return float(h3.cell_area(cell, "m^2"))


def build_adjacency(cells: List[str]) -> Dict[str, List[str]]:
    """Build symmetric hex-grid adjacency mapping (k=1) restricted to the provided cell set.

    Args:
        cells: List of H3 cell index strings in the study region.

    Returns:
        Dict[str, List[str]]: Adjacency dictionary mapping each cell to its within-set neighbors.
    """
    cell_set = set(cells)
    adjacency: Dict[str, List[str]] = {}

    for c in cells:
        neighbors = set(h3.grid_disk(c, 1))
        neighbors.discard(c)
        valid_neighbors = sorted(list(neighbors.intersection(cell_set)))
        adjacency[c] = valid_neighbors

    return adjacency


def pairwise_grid_distance(cells: List[str]) -> np.ndarray:
    """Compute pairwise grid distance (in number of hex steps) across a list of cells.

    Args:
        cells: List of H3 cell index strings.

    Returns:
        np.ndarray: Symmetric (N, N) matrix of integer grid step distances.
    """
    n = len(cells)
    dist_matrix = np.zeros((n, n), dtype=np.int32)

    for i in range(n):
        for j in range(i + 1, n):
            d = h3.grid_distance(cells[i], cells[j])
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d

    return dist_matrix
