"""PyTorch Geometric graph construction and D8 flow-accumulation edge computations."""

# NOTE: Equal-elevation neighbors ARE retained under 'downhill' policy.
# Rationale: preserves graph connectivity for flat terrain.
# If strict-downhill is desired for ablation, change condition to v_elev >= u_elev - 1e-4.

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
from torch_geometric.data import Data

from pragati.config import GraphConfig
from pragati.graph.h3_utils import build_adjacency, cell_to_latlon

# Compass directions mapped to nominal angles (0 = North, 90 = East, etc.)
D8_DIRECTIONS: Dict[str, float] = {
    "N": 0.0,
    "NE": 45.0,
    "E": 90.0,
    "SE": 135.0,
    "S": 180.0,
    "SW": 225.0,
    "W": 270.0,
    "NW": 315.0,
}


def _calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate forward geographic azimuth/bearing from point 1 to point 2 in degrees [0, 360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)

    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    bearing_rad = math.atan2(y, x)
    return float((math.degrees(bearing_rad) + 360.0) % 360.0)


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


def compute_d8_flow_accumulation(
    cells: List[str], terrain: Dict[str, Dict[str, float]]
) -> Dict[str, float]:
    """Compute D8-based upstream drainage area / flow accumulation across an H3 cell network.

    For each cell, determines its steepest-descent neighbor using geographic distance and
    elevation difference. Accumulates upstream contributing cell count starting with base
    weight of 1.0 (self), processing nodes from highest elevation to lowest elevation (topological sort).

    Args:
        cells: List of H3 cell IDs.
        terrain: Dictionary mapping each cell ID to terrain properties (including elevation_m).

    Returns:
        Dict[str, float]: Upstream flow accumulation (contributing cell count including self >= 1.0).
    """
    coords: Dict[str, Tuple[float, float]] = {c: cell_to_latlon(c) for c in cells}
    adjacency = build_adjacency(cells)

    # 1. Determine steepest-descent target for each cell
    downhill_target: Dict[str, Optional[str]] = {}

    for c in cells:
        c_lat, c_lon = coords[c]
        c_elev = float(terrain[c]["elevation_m"])
        neighbors = adjacency.get(c, [])

        best_slope = 0.0
        steepest_neighbor: Optional[str] = None

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
                        steepest_neighbor = n

        downhill_target[c] = steepest_neighbor

    # 2. Accumulate flow: every cell starts with weight 1.0 (its own area)
    flow_acc: Dict[str, float] = {c: 1.0 for c in cells}

    # Sort cells from highest elevation to lowest elevation (ensures upstream accumulates before downstream)
    sorted_cells = sorted(cells, key=lambda c: float(terrain[c]["elevation_m"]), reverse=True)

    for c in sorted_cells:
        target = downhill_target.get(c)
        if target is not None:
            # Transfer accumulated upstream area to the downstream target
            flow_acc[target] += flow_acc[c]

    return flow_acc


def compute_edge_attributes(
    cell_a: str,
    cell_b: str,
    terrain: Dict[str, Dict[str, float]],
    d8_flow_acc: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Compute the 5 frozen baseline terrain edge attributes from source cell_a to target cell_b.

    Attributes:
        1. elevation_diff: elevation_b - elevation_a (metres; negative when flowing downhill)
        2. slope: absolute gradient angle in degrees [0, 90]
        3. flow_direction_compatibility: score in [0.0, 1.0] reflecting alignment with D8 downhill flow
        4. flow_accumulation: upstream drainage accumulation at destination cell_b
        5. distance: great-circle centroid distance in metres

    Args:
        cell_a: Source H3 cell ID.
        cell_b: Destination H3 cell ID.
        terrain: Terrain properties dictionary.
        d8_flow_acc: Precomputed D8 flow accumulation mapping. If None, computed on the fly.

    Returns:
        Dict[str, float]: Dictionary mapping attribute names to float values.
    """
    lat_a, lon_a = cell_to_latlon(cell_a)
    lat_b, lon_b = cell_to_latlon(cell_b)

    elev_a = float(terrain[cell_a]["elevation_m"])
    elev_b = float(terrain[cell_b]["elevation_m"])

    # 1. Elevation difference (dest - src)
    elev_diff = elev_b - elev_a

    # 2. Distance
    dist_m = _haversine_distance_m(lat_a, lon_a, lat_b, lon_b)
    if dist_m < 1e-4:
        dist_m = 1e-4

    # 3. Slope in degrees [0, 90]
    grad_mag = abs(elev_diff) / dist_m
    slope_deg = float(math.degrees(math.atan(grad_mag)))
    slope_deg = max(0.0, min(90.0, slope_deg))

    # 4. Flow direction compatibility:
    # 1.0 if B is strictly downhill from A in D8 sense
    # 0.5 if essentially flat (abs(elev_diff) <= 1e-3)
    # 0.0 if uphill
    # Furthermore, check bearing alignment with cell A's aspect direction
    elev_tol = 1e-3
    if elev_diff < -elev_tol:  # Strictly downhill
        bearing = _calculate_bearing_deg(lat_a, lon_a, lat_b, lon_b)
        aspect_a = float(terrain[cell_a].get("aspect_deg", 0.0))
        # Angular difference between bearing to B and downhill aspect vector of A
        angle_diff = abs((bearing - aspect_a + 180.0) % 360.0 - 180.0)
        # Cosine alignment mapped to [0.5, 1.0] for downhill angles (< 90 deg difference)
        if angle_diff <= 90.0:
            flow_dir_comp = float(0.5 + 0.5 * math.cos(math.radians(angle_diff)))
        else:
            flow_dir_comp = 0.5  # Downhill but angled away from primary aspect
    elif abs(elev_diff) <= elev_tol:
        flow_dir_comp = 0.5  # Equal elevation
    else:
        flow_dir_comp = 0.0  # Uphill flow

    flow_dir_comp = max(0.0, min(1.0, flow_dir_comp))

    # 5. Flow accumulation at destination cell_b
    if d8_flow_acc is not None and cell_b in d8_flow_acc:
        accum_val = float(d8_flow_acc[cell_b])
    else:
        accum_val = float(terrain[cell_b].get("flow_accumulation", 1.0))

    return {
        "elevation_diff": elev_diff,
        "slope": slope_deg,
        "flow_direction_compatibility": flow_dir_comp,
        "flow_accumulation": accum_val,
        "distance": dist_m,
    }


def build_pyg_graph(
    cells: List[str],
    terrain: Dict[str, Dict[str, float]],
    node_feature_matrix: np.ndarray,
    config: GraphConfig,
) -> Data:
    """Build a terrain-aware PyTorch Geometric Data graph on the H3 spatial grid.

    Edges are constructed according to config.direction_policy:
    - 'downhill': creates directed edges only from higher to lower/equal elevation cells.
    - 'bidirectional': retains bidirectional hex edges.

    Args:
        cells: Deterministically ordered list of N cell IDs.
        terrain: Terrain properties dictionary.
        node_feature_matrix: Numpy float32 matrix of shape (N, F).
        config: Graph configuration.

    Returns:
        Data: PyG Data object containing:
            - x: torch.FloatTensor of shape (N, F)
            - edge_index: torch.LongTensor of shape (2, E)
            - edge_attr: torch.FloatTensor of shape (E, 5) or None if not use_edge_attr
            - cell_ids: list[str] (stored as attribute)
            - num_nodes: int (N)
            - meta: dictionary with graph metadata
    """
    n = len(cells)
    cell_to_idx = {c: i for i, c in enumerate(cells)}
    adjacency = build_adjacency(cells)

    # Precalculate global D8 flow accumulation across the network
    d8_flow_acc = compute_d8_flow_accumulation(cells, terrain)

    src_nodes: List[int] = []
    dst_nodes: List[int] = []
    edge_attr_list: List[List[float]] = []

    attr_order = config.edge_attributes

    for u_cell in cells:
        u_idx = cell_to_idx[u_cell]
        u_elev = float(terrain[u_cell]["elevation_m"])
        neighbors = adjacency.get(u_cell, [])

        for v_cell in neighbors:
            v_idx = cell_to_idx[v_cell]
            v_elev = float(terrain[v_cell]["elevation_m"])

            # Filter edges based on direction policy
            if config.direction_policy == "downhill":
                # Downhill policy: flow can only traverse u -> v if v is lower or equal elevation
                if v_elev > u_elev + 1e-4:
                    continue

            src_nodes.append(u_idx)
            dst_nodes.append(v_idx)

            if config.use_edge_attr:
                edge_dict = compute_edge_attributes(u_cell, v_cell, terrain, d8_flow_acc)
                edge_attr_list.append([edge_dict[name] for name in attr_order])

    # Convert to PyTorch tensors
    x_tensor = torch.tensor(node_feature_matrix, dtype=torch.float32)

    if src_nodes:
        edge_index_tensor = torch.tensor([src_nodes, dst_nodes], dtype=torch.int64)
    else:
        edge_index_tensor = torch.empty((2, 0), dtype=torch.int64)

    if config.use_edge_attr and edge_attr_list:
        edge_attr_tensor = torch.tensor(edge_attr_list, dtype=torch.float32)
    else:
        edge_attr_tensor = None

    data = Data(
        x=x_tensor,
        edge_index=edge_index_tensor,
        edge_attr=edge_attr_tensor,
    )
    # Plain attributes
    data.cell_ids = list(cells)
    data.num_nodes = n
    data.meta = {
        "h3_resolution": 9,
        "mode": config.mode,
        "direction_policy": config.direction_policy,
        "use_edge_attr": config.use_edge_attr,
    }

    return data


def build_flat_graph(
    cells: List[str], node_feature_matrix: np.ndarray, config: GraphConfig
) -> Data:
    """Build an undirected/bidirectional flat spatial graph with NO edge attributes for RQ1 ablation.

    Args:
        cells: Deterministically ordered list of N cell IDs.
        node_feature_matrix: Numpy float32 matrix of shape (N, F).
        config: Graph configuration.

    Returns:
        Data: PyG Data object with edge_attr=None and bidirectional hex topology.
    """
    n = len(cells)
    cell_to_idx = {c: i for i, c in enumerate(cells)}
    adjacency = build_adjacency(cells)

    src_nodes: List[int] = []
    dst_nodes: List[int] = []

    for u_cell in cells:
        u_idx = cell_to_idx[u_cell]
        for v_cell in adjacency.get(u_cell, []):
            src_nodes.append(u_idx)
            dst_nodes.append(cell_to_idx[v_cell])

    x_tensor = torch.tensor(node_feature_matrix, dtype=torch.float32)
    edge_index_tensor = torch.tensor([src_nodes, dst_nodes], dtype=torch.int64)

    data = Data(
        x=x_tensor,
        edge_index=edge_index_tensor,
        edge_attr=None,
    )
    data.cell_ids = list(cells)
    data.num_nodes = n
    data.meta = {
        "h3_resolution": 9,
        "mode": "flat",
        "direction_policy": "bidirectional",
        "use_edge_attr": False,
    }

    return data
