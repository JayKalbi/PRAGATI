"""Unit tests for H3 grid utilities in pragati.graph.h3_utils."""

import numpy as np
from pragati.graph.h3_utils import (
    build_adjacency,
    cell_area_m2,
    cell_to_latlon,
    create_hex_grid,
    get_neighbors,
    pairwise_grid_distance,
)


def test_create_hex_grid_radius_1() -> None:
    """Verify create_hex_grid with radius=1 returns 7 cells (1 center + 6 ring-1 neighbors)."""
    cells = create_hex_grid(
        center_lat=19.0760,
        center_lon=72.8777,
        radius_cells=1,
        resolution=9,
    )
    assert len(cells) == 7
    assert len(set(cells)) == 7  # All unique


def test_get_neighbors_res_9() -> None:
    """Verify get_neighbors returns exactly 6 cells at resolution 9 for a center cell."""
    grid = create_hex_grid(center_lat=19.0760, center_lon=72.8777, radius_cells=1, resolution=9)
    # The center is one of these; get neighbors of the first cell
    cell = grid[0]
    neighbors = get_neighbors(cell, k=1)
    assert len(neighbors) == 6
    assert cell not in neighbors


def test_adjacency_symmetry() -> None:
    """Verify adjacency is symmetric: if b in adj[a] then a in adj[b]."""
    cells = create_hex_grid(
        center_lat=19.0760,
        center_lon=72.8777,
        radius_cells=2,
        resolution=9,
    )
    adj = build_adjacency(cells)

    for a, neighbors in adj.items():
        for b in neighbors:
            assert a in adj[b], f"Symmetry broken: {b} is in adj[{a}], but {a} not in adj[{b}]"


def test_cell_area_res_9() -> None:
    """Verify cell area for resolution 9 is between 50,000 and 200,000 m² (~0.1 km²)."""
    grid = create_hex_grid(center_lat=19.0760, center_lon=72.8777, radius_cells=0, resolution=9)
    cell = grid[0]
    area = cell_area_m2(cell)
    assert 50000.0 <= area <= 200000.0, f"Area {area} m² outside expected range for res 9."


def test_cell_to_latlon() -> None:
    """Verify cell_to_latlon returns reasonable coordinates close to input."""
    lat_in, lon_in = 19.0760, 72.8777
    grid = create_hex_grid(center_lat=lat_in, center_lon=lon_in, radius_cells=0, resolution=9)
    lat_out, lon_out = cell_to_latlon(grid[0])
    assert abs(lat_out - lat_in) < 0.05
    assert abs(lon_out - lon_in) < 0.05


def test_reproducibility() -> None:
    """Verify identical inputs yield identical ordered cell lists."""
    g1 = create_hex_grid(center_lat=19.0760, center_lon=72.8777, radius_cells=2, resolution=9)
    g2 = create_hex_grid(center_lat=19.0760, center_lon=72.8777, radius_cells=2, resolution=9)
    assert g1 == g2


def test_pairwise_grid_distance() -> None:
    """Verify pairwise grid distance matrix properties."""
    cells = create_hex_grid(center_lat=19.0760, center_lon=72.8777, radius_cells=1, resolution=9)
    dist = pairwise_grid_distance(cells)

    assert dist.shape == (7, 7)
    np.testing.assert_array_equal(np.diag(dist), np.zeros(7))
    np.testing.assert_array_equal(dist, dist.T)  # Symmetric
    assert np.all(dist >= 0)
    assert np.all(dist <= 2)  # In a radius 1 disk, max distance between any two nodes is 2
