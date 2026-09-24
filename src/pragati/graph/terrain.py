"""Synthetic terrain generation and topographic attribute computation for H3 grids."""

import math
from typing import Any, Dict, List, Tuple
import numpy as np

from pragati.graph.h3_utils import build_adjacency, cell_to_latlon
from pragati.utils.seeding import get_rng, set_global_seed


def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance between two points in metres using Haversine formula."""
    r = 6371000.0  # Earth radius in metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return float(r * c)


def generate_synthetic_terrain(
    cells: List[str],
    seed: int,
    base_elevation_m: float = 10.0,
    num_hills: int = 5,
    hill_height_range: Tuple[float, float] = (2.0, 8.0),
    hill_radius_m: float = 300.0,
    noise_std_m: float = 0.3,
) -> Dict[str, Dict[str, float]]:
    """Generate physically plausible synthetic terrain for an H3 cell network.

    Elevation is modeled as a sum of 2D Gaussian hills plus zero-mean Gaussian noise.
    Slope, aspect, and flow accumulation are derived from local neighborhood gradients.

    Args:
        cells: List of H3 cell index strings.
        seed: Random seed for deterministic generation.
        base_elevation_m: Nominal baseline elevation in metres.
        num_hills: Number of Gaussian elevation peaks to place.
        hill_height_range: (min_height, max_height) range for hills in metres.
        hill_radius_m: Characteristic spread/standard deviation of Gaussian hills in metres.
        noise_std_m: Standard deviation of micro-topographic Gaussian noise.

    Returns:
        Dict[str, Dict[str, float]]: Dictionary mapping cell_id to terrain properties:
            {
                cell_id: {
                    "elevation_m": float,
                    "slope_deg": float,
                    "aspect_deg": float,
                    "flow_accumulation": float
                }
            }
    """
    set_global_seed(seed)
    rng = get_rng(seed)

    coords: Dict[str, Tuple[float, float]] = {c: cell_to_latlon(c) for c in cells}
    lats = np.array([coords[c][0] for c in cells])
    lons = np.array([coords[c][1] for c in cells])

    # 1. Randomly place Gaussian hill centres within or near the grid bounding box
    min_lat, max_lat = float(lats.min()), float(lats.max())
    min_lon, max_lon = float(lons.min()), float(lons.max())

    hill_lats = rng.uniform(min_lat, max_lat, size=num_hills)
    hill_lons = rng.uniform(min_lon, max_lon, size=num_hills)
    hill_heights = rng.uniform(hill_height_range[0], hill_height_range[1], size=num_hills)

    # 2. Compute elevations per cell
    elevations: Dict[str, float] = {}
    for c in cells:
        c_lat, c_lon = coords[c]
        elev = base_elevation_m

        for h_lat, h_lon, h_height in zip(hill_lats, hill_lons, hill_heights):
            dist_m = _haversine_distance_m(c_lat, c_lon, h_lat, h_lon)
            elev += float(h_height * math.exp(-0.5 * (dist_m / hill_radius_m) ** 2))

        # Add Gaussian noise
        noise = float(rng.normal(0.0, noise_std_m))
        elevations[c] = float(elev + noise)

    # 3. Compute slope, aspect, and flow accumulation from adjacency
    adjacency = build_adjacency(cells)
    r_earth = 6371000.0

    terrain_dict: Dict[str, Dict[str, float]] = {}

    for c in cells:
        c_lat, c_lon = coords[c]
        c_elev = elevations[c]
        neighbors = adjacency.get(c, [])

        if not neighbors:
            terrain_dict[c] = {
                "elevation_m": c_elev,
                "slope_deg": 0.0,
                "aspect_deg": 0.0,
                "flow_accumulation": 1.0,
            }
            continue

        # Fit local planar gradient: dz/dx (east) and dz/dy (north)
        dx_list: List[float] = []
        dy_list: List[float] = []
        dz_list: List[float] = []

        for n in neighbors:
            n_lat, n_lon = coords[n]
            n_elev = elevations[n]

            # Approximate local metric offsets
            d_north = math.radians(n_lat - c_lat) * r_earth
            d_east = math.radians(n_lon - c_lon) * r_earth * math.cos(math.radians(c_lat))
            d_z = n_elev - c_elev

            dx_list.append(d_east)
            dy_list.append(d_north)
            dz_list.append(d_z)

        # Least-squares fit: [dx, dy] * [dz_dx, dz_dy]^T = dz
        a_mat = np.column_stack([dx_list, dy_list])
        b_vec = np.array(dz_list)

        try:
            grad, _, _, _ = np.linalg.lstsq(a_mat, b_vec, rcond=None)
            dz_dx, dz_dy = float(grad[0]), float(grad[1])
        except Exception:
            dz_dx, dz_dy = 0.0, 0.0

        # Gradient magnitude -> slope in degrees [0, 90]
        grad_mag = math.sqrt(dz_dx**2 + dz_dy**2)
        slope_deg = float(math.degrees(math.atan(grad_mag)))
        slope_deg = max(0.0, min(90.0, slope_deg))

        # Downhill direction for aspect (0 deg = North, 90 deg = East)
        # Downhill vector is (-dz_dx, -dz_dy)
        aspect_deg = float(math.degrees(math.atan2(-dz_dx, -dz_dy)) % 360.0)

        # 4. Proxy flow accumulation based on relative depression/downhill index
        # Cells lower than all/most neighbors accumulate more flow
        higher_neighbors = sum(1 for n in neighbors if elevations[n] > c_elev)
        flow_accum = float(1.0 + (higher_neighbors / len(neighbors)) * 10.0)

        terrain_dict[c] = {
            "elevation_m": c_elev,
            "slope_deg": slope_deg,
            "aspect_deg": aspect_deg,
            "flow_accumulation": flow_accum,
        }

    return terrain_dict
