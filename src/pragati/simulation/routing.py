"""D8 single-receiver flow routing and reverse upstream connectivity on H3 grids."""

from typing import Dict, List, Optional, Tuple
from pragati.graph.graph_builder import _haversine_distance_m
from pragati.graph.h3_utils import build_adjacency, cell_to_latlon


def compute_d8_receivers(
    cells: List[str], terrain: Dict[str, Dict[str, float]]
) -> Dict[str, Optional[str]]:
    """Determine the single steepest-descent D8 downstream receiver for each H3 cell.

    If a cell has no strictly downhill neighbor (elevation drop > 1e-4 m), it is designated
    as a terminal hydrological sink and its receiver is set to None.

    Args:
        cells: Deterministic list of H3 cell IDs.
        terrain: Dictionary mapping each cell ID to its terrain attributes, containing 'elevation_m'.

    Returns:
        Dict[str, Optional[str]]: Mapping from each cell ID to its downstream receiver ID (or None if a sink).
    """
    coords: Dict[str, Tuple[float, float]] = {c: cell_to_latlon(c) for c in cells}
    adjacency = build_adjacency(cells)

    receivers: Dict[str, Optional[str]] = {}

    for c in cells:
        c_lat, c_lon = coords[c]
        c_elev = float(terrain[c]["elevation_m"])
        neighbors = adjacency.get(c, [])

        best_slope = 0.0
        steepest_receiver: Optional[str] = None

        for n in neighbors:
            n_lat, n_lon = coords[n]
            n_elev = float(terrain[n]["elevation_m"])
            elev_drop = c_elev - n_elev

            if elev_drop > 1e-4:  # Strictly downhill
                dist_m = _haversine_distance_m(c_lat, c_lon, n_lat, n_lon)
                if dist_m > 0:
                    slope = elev_drop / dist_m
                    if slope > best_slope:
                        best_slope = slope
                        steepest_receiver = n

        receivers[c] = steepest_receiver

    return receivers


def compute_reverse_routing(
    cells: List[str], receivers: Dict[str, Optional[str]]
) -> Dict[str, List[str]]:
    """Compute the reverse upstream contributor list for each cell.

    Args:
        cells: Deterministic list of H3 cell IDs.
        receivers: Mapping from each cell ID to its downstream receiver ID.

    Returns:
        Dict[str, List[str]]: Mapping from each cell ID to the sorted list of cells that drain into it.
    """
    reverse: Dict[str, List[str]] = {c: [] for c in cells}

    for u in cells:
        target = receivers.get(u)
        if target is not None and target in reverse:
            reverse[target].append(u)

    # Sort upstream lists for strict determinism
    for c in cells:
        reverse[c].sort()

    return reverse
