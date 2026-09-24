"""Unit tests for synthetic terrain generation in pragati.graph.terrain."""

from pragati.graph.h3_utils import create_hex_grid
from pragati.graph.terrain import generate_synthetic_terrain


def test_terrain_reproducibility() -> None:
    """Verify same seed produces identical terrain dictionaries."""
    cells = create_hex_grid(19.0760, 72.8777, radius_cells=1, resolution=9)
    t1 = generate_synthetic_terrain(cells, seed=42)
    t2 = generate_synthetic_terrain(cells, seed=42)

    assert t1 == t2


def test_terrain_different_seeds() -> None:
    """Verify different seeds produce different elevation profiles."""
    cells = create_hex_grid(19.0760, 72.8777, radius_cells=1, resolution=9)
    t1 = generate_synthetic_terrain(cells, seed=42)
    t2 = generate_synthetic_terrain(cells, seed=99)

    elevs1 = [t1[c]["elevation_m"] for c in cells]
    elevs2 = [t2[c]["elevation_m"] for c in cells]
    assert elevs1 != elevs2


def test_terrain_keys_and_bounds() -> None:
    """Verify each cell contains all 4 keys and slope, aspect, and elevation satisfy physical bounds."""
    cells = create_hex_grid(19.0760, 72.8777, radius_cells=2, resolution=9)
    base_elev = 10.0
    hill_range = (2.0, 8.0)
    noise_std = 0.3

    terrain = generate_synthetic_terrain(
        cells,
        seed=1337,
        base_elevation_m=base_elev,
        hill_height_range=hill_range,
        noise_std_m=noise_std,
    )

    required_keys = {"elevation_m", "slope_deg", "aspect_deg", "flow_accumulation"}

    for c in cells:
        assert c in terrain
        assert set(terrain[c].keys()) == required_keys

        # Slope bounds in [0, 90] degrees
        assert 0.0 <= terrain[c]["slope_deg"] <= 90.0

        # Aspect bounds in [0, 360] degrees
        assert 0.0 <= terrain[c]["aspect_deg"] <= 360.0

        # Flow accumulation >= 1.0
        assert terrain[c]["flow_accumulation"] >= 1.0

        # Elevation within physical expected envelope
        # base_elev - 2*hill_height_range[1] <= elev <= base_elev + num_hills * hill_height_range[1] + noise_margin
        min_expected = base_elev - 2 * hill_range[1]
        max_expected = base_elev + 10 * hill_range[1] + 5 * noise_std
        assert min_expected <= terrain[c]["elevation_m"] <= max_expected
