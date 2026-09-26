"""Smoke test and demonstration script for PRAGATI PyG graph construction.

Constructs an H3 resolution 9 grid (radius=3, 37 cells) around Mumbai coordinates,
generates synthetic terrain, builds both terrain-aware and flat PyG graphs, and
saves the output graphs under data/synthetic/.
"""

from pathlib import Path
import torch

from pragati.config import GraphConfig
from pragati.graph.graph_builder import build_flat_graph, build_pyg_graph
from pragati.graph.h3_utils import create_hex_grid
from pragati.graph.node_features import assemble_node_features
from pragati.graph.terrain import generate_synthetic_terrain
from pragati.utils.seeding import set_global_seed


def main() -> None:
    # 1. Deterministic seeding
    set_global_seed(42)

    # 2. Centroid around Mumbai (19.076, 72.8777) at H3 Res 9
    center_lat, center_lon = 19.0760, 72.8777
    h3_res = 9
    radius = 3  # Disk of radius 3 yields 1 + 6 + 12 + 18 = 37 cells

    print(f"Generating H3 grid at resolution {h3_res} around ({center_lat}, {center_lon})...")
    cells = create_hex_grid(center_lat, center_lon, radius_cells=radius, resolution=h3_res)
    print(f"Total H3 cells: {len(cells)}")

    # 3. Generate synthetic terrain
    print("Generating synthetic terrain...")
    terrain = generate_synthetic_terrain(cells, seed=42)

    # 4. Assemble node features
    print("Assembling node features matrix...")
    node_features = assemble_node_features(cells, terrain)
    print(f"Node feature matrix shape: {node_features.shape}")

    # 5. Build Terrain-Aware PyG graph (frozen baseline)
    cfg_terrain = GraphConfig(
        mode="terrain_aware",
        direction_policy="downhill",
        use_edge_attr=True,
    )
    graph_terrain = build_pyg_graph(cells, terrain, node_features, cfg_terrain)

    print("\n--- Terrain-Aware Graph (Frozen Baseline) ---")
    print(f"Number of nodes (N): {graph_terrain.num_nodes}")
    print(f"Number of directed edges (E): {graph_terrain.edge_index.shape[1]}")
    print(f"Node feature tensor x shape: {graph_terrain.x.shape}")
    print(f"Edge attribute tensor shape: {graph_terrain.edge_attr.shape if graph_terrain.edge_attr is not None else None}")
    print(f"Graph metadata: {graph_terrain.meta}")

    # 6. Build Flat PyG graph (RQ1 ablation baseline)
    cfg_flat = GraphConfig(
        mode="flat",
        direction_policy="bidirectional",
        use_edge_attr=False,
    )
    graph_flat = build_flat_graph(cells, node_features, cfg_flat)

    print("\n--- Flat Graph (RQ1 Ablation Baseline) ---")
    print(f"Number of nodes (N): {graph_flat.num_nodes}")
    print(f"Number of bidirectional edges (E): {graph_flat.edge_index.shape[1]}")
    print(f"Node feature tensor x shape: {graph_flat.x.shape}")
    print(f"Edge attribute tensor: {graph_flat.edge_attr}")
    print(f"Graph metadata: {graph_flat.meta}")

    # 7. Save graph objects
    output_dir = Path(__file__).resolve().parent.parent / "data" / "synthetic"
    output_dir.mkdir(parents=True, exist_ok=True)

    terrain_path = output_dir / "demo_graph_terrain.pt"
    flat_path = output_dir / "demo_graph_flat.pt"

    torch.save(graph_terrain, terrain_path)
    torch.save(graph_flat, flat_path)

    print(f"\nSaved terrain-aware graph to: {terrain_path}")
    print(f"Saved flat graph to: {flat_path}")
    print("Demo graph construction completed successfully.")


if __name__ == "__main__":
    main()
