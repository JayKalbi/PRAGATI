"""Node feature assembly and encoding utilities for PRAGATI."""

import math
from typing import Dict, List, Optional
import numpy as np


def assemble_node_features(
    cells: List[str],
    terrain: Dict[str, Dict[str, float]],
    depth_per_cell: Optional[Dict[str, float]] = None,
    rainfall_per_cell: Optional[Dict[str, float]] = None,
    quality_per_cell: Optional[Dict[str, float]] = None,
    feature_names: Optional[List[str]] = None,
) -> np.ndarray:
    """Assemble a 2D float32 numpy feature matrix for an ordered list of H3 cells.

    Supports cyclical trigonometric encoding for aspect and slope:
    - aspect_sin = sin(radians(aspect_deg))
    - aspect_cos = cos(radians(aspect_deg))
    - slope_sin  = sin(radians(slope_deg))
    - slope_cos  = cos(radians(slope_deg))

    Args:
        cells: Ordered list of N H3 cell IDs.
        terrain: Dictionary containing terrain properties per cell.
        depth_per_cell: Inundation depth in metres per cell (default 0.0).
        rainfall_per_cell: Rainfall in mm per cell (default 0.0).
        quality_per_cell: Sensor quality score in [0.0, 1.0] per cell (default 1.0).
        feature_names: List of column names to extract in order. Defaults to:
            ["depth", "rainfall", "elevation", "slope_sin", "slope_cos",
             "aspect_sin", "aspect_cos", "flow_accumulation", "sensor_quality"]

    Returns:
        np.ndarray: Matrix of shape (N, len(feature_names)) with dtype float32.
    """
    if feature_names is None:
        feature_names = [
            "depth",
            "rainfall",
            "elevation",
            "slope_sin",
            "slope_cos",
            "aspect_sin",
            "aspect_cos",
            "flow_accumulation",
            "sensor_quality",
        ]

    depth_map = depth_per_cell or {}
    rain_map = rainfall_per_cell or {}
    qual_map = quality_per_cell or {}

    rows: List[List[float]] = []

    for cell in cells:
        cell_terrain = terrain.get(cell, {})
        elev = float(cell_terrain.get("elevation_m", 0.0))
        slope = float(cell_terrain.get("slope_deg", 0.0))
        aspect = float(cell_terrain.get("aspect_deg", 0.0))
        flow_acc = float(cell_terrain.get("flow_accumulation", 1.0))

        depth = float(depth_map.get(cell, 0.0))
        rain = float(rain_map.get(cell, 0.0))
        qual = float(qual_map.get(cell, 1.0))

        # Cyclical transformations
        slope_rad = math.radians(slope)
        slope_sin = float(math.sin(slope_rad))
        slope_cos = float(math.cos(slope_rad))

        aspect_rad = math.radians(aspect)
        aspect_sin = float(math.sin(aspect_rad))
        aspect_cos = float(math.cos(aspect_rad))

        feature_lookup: Dict[str, float] = {
            "depth": depth,
            "rainfall": rain,
            "elevation": elev,
            "slope": slope,
            "slope_sin": slope_sin,
            "slope_cos": slope_cos,
            "aspect": aspect,
            "aspect_sin": aspect_sin,
            "aspect_cos": aspect_cos,
            "flow_accumulation": flow_acc,
            "sensor_quality": qual,
        }

        row = [feature_lookup.get(feat, 0.0) for feat in feature_names]
        rows.append(row)

    return np.array(rows, dtype=np.float32)
