"""Run a demonstration of the Rapid Terrain-Driven Surface-Flow Simulator.

Generates a 37-cell H3 grid centered on Mumbai (19.0760, 72.8777) at resolution 9,
synthesizes terrain (elevation, slope, aspect) with seed 42, runs a 24-step (6-hour)
simulation under continuous rainfall, reports key metrics, and saves the trajectory.
"""

from __future__ import annotations

import logging
from pathlib import Path
import numpy as np

from pragati.config import SimulationConfig
from pragati.graph.h3_utils import create_hex_grid
from pragati.graph.terrain import generate_synthetic_terrain
from pragati.simulation.routing import compute_d8_receivers
from pragati.simulation.simulator import SurfaceFlowSimulator
from pragati.simulation.state import SimulationState
from pragati.utils.seeding import set_global_seed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger("pragati.simulation.demo")

    # 1. Deterministic seeding
    set_global_seed(42)

    # 2. Build 37-cell H3 grid (resolution 9, radius 3)
    lat, lng = 19.0760, 72.8777
    res = 9
    radius = 3
    cells = create_hex_grid(lat, lng, radius_cells=radius, resolution=res)
    n_cells = len(cells)
    logger.info(f"Generated H3 grid: {n_cells} cells at res {res}, radius {radius}")

    # 3. Generate synthetic terrain
    terrain = generate_synthetic_terrain(cells, seed=42)
    receivers = compute_d8_receivers(cells, terrain)
    num_sinks = sum(1 for r in receivers.values() if r is None)
    logger.info(f"Identified {num_sinks} sink(s) among {n_cells} cells")

    # 4. Simulation Configuration
    sim_cfg = SimulationConfig(
        timestep_minutes=15,
        manning_n=0.03,
        runoff_coefficient=0.20,
        cfl_safety_factor=0.5,
        infiltration_model="exponential_decay",
        infiltration_initial_mm_per_hr=20.0,
        infiltration_residual_mm_per_hr=2.0,
        infiltration_decay_constant_hr=1.0,
        max_depth_m=5.0,
    )
    simulator = SurfaceFlowSimulator(cells, terrain, sim_cfg)

    # 5. Initialize state with zero depth
    initial_state = SimulationState(
        cells=cells,
        depth_m=np.zeros(n_cells, dtype=np.float64),
        cumulative_infiltrated_m=np.zeros(n_cells, dtype=np.float64),
        cumulative_rainfall_m=np.zeros(n_cells, dtype=np.float64),
        time_step=0,
    )

    # 6. Run 24 steps (6 hours) with 10.0 mm/step constant rainfall
    num_steps = 24
    rainfall_series = np.full((num_steps, n_cells), 10.0, dtype=np.float64)

    logger.info(f"Running simulation for {num_steps} steps (dt=15 min, rain=10 mm/step)...")
    trajectory = simulator.run(initial_state, rainfall_series, num_steps=num_steps)

    # 7. Compute summary metrics
    final_depths = trajectory.depths_m[-1]
    peak_depth = float(np.max(trajectory.depths_m))
    mean_final_depth = float(np.mean(final_depths))
    mass_balance_error_m3 = trajectory.mass_balance_error(areas_m2=simulator.areas_m2)
    rel_mass_balance_error = trajectory.relative_mass_balance_error(
        areas_m2=simulator.areas_m2, runoff_coefficient=sim_cfg.runoff_coefficient
    )

    print("=" * 60)
    print("PRAGATI Surface-Flow Simulator (Phase 3A Demo)")
    print("=" * 60)
    print(f"Number of cells:                  {n_cells}")
    print(f"Number of sinks:                  {num_sinks}")
    print(f"Simulation steps:                 {num_steps} ({num_steps * 15 / 60:.1f} hours)")
    print(f"Rainfall per step:                10.0 mm")
    print(f"Peak depth across domain & time:  {peak_depth:.4f} m")
    print(f"Mean depth at final step:         {mean_final_depth:.4f} m")
    print(f"Absolute mass balance error:      {mass_balance_error_m3:.4e} m^3")
    print(f"Relative mass balance error:      {rel_mass_balance_error:.4e}")
    print("=" * 60)

    # 8. Save trajectory
    out_dir = Path("data/synthetic")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "demo_trajectory.npz"
    trajectory.save(out_path)
    logger.info(f"Saved trajectory to {out_path}")


if __name__ == "__main__":
    main()
