"""Unit tests for PyG graph construction, D8 flow accumulation, and edge attributes."""

import math
import numpy as np
import pytest
import torch

from pragati.config import GraphConfig
from pragati.graph.graph_builder import (
    build_flat_graph,
    build_pyg_graph,
    compute_d8_flow_accumulation,
    compute_edge_attributes,
)
from pragati.graph.h3_utils import create_hex_grid
from pragati.graph.node_features import assemble_node_features
from pragati.graph.terrain import generate_synthetic_terrain


@pytest.fixture
def sample_graph_data():
    """Generate deterministic sample cells, terrain, and features for testing."""
    cells = create_hex_grid(center_lat=19.0760, center_lon=72.8777, radius_cells=2, resolution=9)
    terrain = generate_synthetic_terrain(cells, seed=42)
    features = assemble_node_features(cells, terrain)
    return cells, terrain, features


def test_d8_flow_accumulation_sums_to_at_least_num_cells(sample_graph_data) -> None:
    """Verify flow accumulation across all nodes is >= total number of cells (each cell is >= 1.0)."""
    cells, terrain, _ = sample_graph_data
    flow_acc = compute_d8_flow_accumulation(cells, terrain)

    assert len(flow_acc) == len(cells)
    total_acc = sum(flow_acc.values())
    assert total_acc >= len(cells)
    for c in cells:
        assert flow_acc[c] >= 1.0


def test_d8_flow_accumulation_downhill_only(sample_graph_data) -> None:
    """Verify that highest elevation cells have accumulation == 1.0 (no upstream flow)."""
    cells, terrain, _ = sample_graph_data
    flow_acc = compute_d8_flow_accumulation(cells, terrain)

    highest_cell = max(cells, key=lambda c: terrain[c]["elevation_m"])
    # The peak node has no contributing higher neighbors
    assert flow_acc[highest_cell] == 1.0


def test_edge_attr_shape_matches_config(sample_graph_data) -> None:
    """Verify that edge_attr has shape (E, 5) matching config.edge_attributes."""
    cells, terrain, features = sample_graph_data
    cfg = GraphConfig(mode="terrain_aware", direction_policy="downhill", use_edge_attr=True)

    data = build_pyg_graph(cells, terrain, features, cfg)
    assert data.edge_attr is not None
    assert data.edge_attr.ndim == 2
    assert data.edge_attr.shape[0] == data.edge_index.shape[1]
    assert data.edge_attr.shape[1] == 5


def test_edge_attr_column_order_matches_config(sample_graph_data) -> None:
    """Verify edge attributes column ordering strictly adheres to the frozen baseline."""
    cells, terrain, _ = sample_graph_data
    cell_a = cells[0]
    cell_b = cells[1]

    attr_dict = compute_edge_attributes(cell_a, cell_b, terrain)
    cfg = GraphConfig()

    expected_cols = [
        "elevation_diff",
        "slope",
        "flow_direction_compatibility",
        "flow_accumulation",
        "distance",
    ]
    assert cfg.edge_attributes == expected_cols
    for col in expected_cols:
        assert col in attr_dict


def test_downhill_policy_keeps_only_downhill_edges(sample_graph_data) -> None:
    """Verify downhill direction policy keeps only edges where dest elevation <= src elevation."""
    cells, terrain, features = sample_graph_data
    cfg = GraphConfig(direction_policy="downhill", use_edge_attr=True)

    data = build_pyg_graph(cells, terrain, features, cfg)
    edge_index = data.edge_index.numpy()

    for idx in range(edge_index.shape[1]):
        u_idx, v_idx = edge_index[0, idx], edge_index[1, idx]
        u_elev = terrain[cells[u_idx]]["elevation_m"]
        v_elev = terrain[cells[v_idx]]["elevation_m"]
        assert v_elev <= u_elev + 1e-4, f"Uphill edge found: {u_elev} -> {v_elev}"


def test_bidirectional_policy_keeps_both_directions(sample_graph_data) -> None:
    """Verify bidirectional direction policy retains both (u, v) and (v, u) edges."""
    cells, terrain, features = sample_graph_data
    cfg = GraphConfig(direction_policy="bidirectional", use_edge_attr=True)

    data = build_pyg_graph(cells, terrain, features, cfg)
    edge_set = set(zip(data.edge_index[0].tolist(), data.edge_index[1].tolist()))

    for u, v in edge_set:
        assert (v, u) in edge_set, f"Edge ({u}, {v}) missing reverse in bidirectional graph"


def test_flat_mode_has_no_edge_attr(sample_graph_data) -> None:
    """Verify that flat graph variant has edge_attr=None for RQ1 ablation baseline."""
    cells, _, features = sample_graph_data
    cfg = GraphConfig(mode="flat", use_edge_attr=False)

    data = build_flat_graph(cells, features, cfg)
    assert data.edge_attr is None
    assert data.meta["mode"] == "flat"
    assert data.meta["use_edge_attr"] is False


def test_flat_mode_is_symmetric(sample_graph_data) -> None:
    """Verify that flat graph edge topology is strictly symmetric."""
    cells, _, features = sample_graph_data
    cfg = GraphConfig(mode="flat")

    data = build_flat_graph(cells, features, cfg)
    edge_set = set(zip(data.edge_index[0].tolist(), data.edge_index[1].tolist()))

    for u, v in edge_set:
        assert (v, u) in edge_set


def test_graph_determinism_same_inputs_same_output(sample_graph_data) -> None:
    """Verify deterministic reproducibility for identical inputs."""
    cells, terrain, features = sample_graph_data
    cfg = GraphConfig(mode="terrain_aware", direction_policy="downhill")

    data1 = build_pyg_graph(cells, terrain, features, cfg)
    data2 = build_pyg_graph(cells, terrain, features, cfg)

    assert torch.equal(data1.x, data2.x)
    assert torch.equal(data1.edge_index, data2.edge_index)
    assert torch.equal(data1.edge_attr, data2.edge_attr)
    assert data1.cell_ids == data2.cell_ids


def test_node_feature_shape_and_dtype(sample_graph_data) -> None:
    """Verify node feature matrix dimensions, float32 type, and non-empty rows."""
    cells, terrain, _ = sample_graph_data
    custom_feats = ["depth", "elevation", "slope_sin", "slope_cos"]

    feat_matrix = assemble_node_features(cells, terrain, feature_names=custom_feats)
    assert feat_matrix.shape == (len(cells), 4)
    assert feat_matrix.dtype == np.float32


def test_flow_direction_compatibility_bounds(sample_graph_data) -> None:
    """Verify flow_direction_compatibility is strictly bounded in [0.0, 1.0]."""
    cells, terrain, _ = sample_graph_data

    for i in range(len(cells) - 1):
        attr = compute_edge_attributes(cells[i], cells[i + 1], terrain)
        val = attr["flow_direction_compatibility"]
        assert 0.0 <= val <= 1.0, f"Out of bounds compatibility value: {val}"


def test_cyclic_aspect_encoding_correctness() -> None:
    """Verify aspect=0 and aspect=360 yield identical sin and cos cyclic encodings."""
    cells = ["c1", "c2"]
    terrain = {
        "c1": {"elevation_m": 10.0, "slope_deg": 15.0, "aspect_deg": 0.0, "flow_accumulation": 1.0},
        "c2": {"elevation_m": 10.0, "slope_deg": 15.0, "aspect_deg": 360.0, "flow_accumulation": 1.0},
    }
    feats = assemble_node_features(cells, terrain, feature_names=["aspect_sin", "aspect_cos"])

    # c1 aspect=0 deg -> sin=0.0, cos=1.0
    # c2 aspect=360 deg -> sin=0.0, cos=1.0
    np.testing.assert_allclose(feats[0], feats[1], atol=1e-6)
    assert abs(feats[0, 0] - 0.0) < 1e-6
    assert abs(feats[0, 1] - 1.0) < 1e-6
