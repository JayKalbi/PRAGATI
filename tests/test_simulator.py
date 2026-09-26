"""Unit tests for the Rapid Terrain-Driven Surface-Flow Simulator."""

from pathlib import Path
import numpy as np
import pytest

from pragati.config import SimulationConfig
from pragati.graph.h3_utils import create_hex_grid
from pragati.graph.terrain import generate_synthetic_terrain
from pragati.simulation.routing import compute_d8_receivers, compute_reverse_routing
from pragati.simulation.simulator import SurfaceFlowSimulator
from pragati.simulation.state import SimulationState
from pragati.simulation.trajectory import SimulationTrajectory


@pytest.fixture
def sim_setup():
    """Build a deterministic 19-cell test grid with synthetic terrain."""
    cells = create_hex_grid(center_lat=19.0760, center_lon=72.8777, radius_cells=2, resolution=9)
    terrain = generate_synthetic_terrain(cells, seed=42)
    cfg = SimulationConfig(
        manning_n=0.03,
        runoff_coefficient=0.20,
        cfl_safety_factor=0.5,
        infiltration_model="exponential_decay",
        infiltration_initial_mm_per_hr=10.0,
        infiltration_residual_mm_per_hr=2.0,
    )
    sim = SurfaceFlowSimulator(cells, terrain, cfg, timestep_minutes=15)
    return cells, terrain, cfg, sim


def test_receivers_are_strictly_downhill_or_none(sim_setup) -> None:
    """Verify each receiver is either strictly lower elevation or None (terminal sink)."""
    cells, terrain, _, _ = sim_setup
    receivers = compute_d8_receivers(cells, terrain)

    for c, target in receivers.items():
        if target is not None:
            elev_c = terrain[c]["elevation_m"]
            elev_target = terrain[target]["elevation_m"]
            assert elev_target < elev_c - 1e-4, f"Target {target} not lower than {c}"


def test_reverse_routing_consistency(sim_setup) -> None:
    """Verify reverse routing consistency: u in upstreams[v] iff receivers[u] == v."""
    cells, terrain, _, _ = sim_setup
    receivers = compute_d8_receivers(cells, terrain)
    upstreams = compute_reverse_routing(cells, receivers)

    for u in cells:
        target = receivers[u]
        if target is not None:
            assert u in upstreams[target], f"{u} drains to {target}, but not in upstreams[{target}]"

    for v in cells:
        for u in upstreams[v]:
            assert receivers[u] == v, f"{u} in upstreams[{v}], but receivers[{u}] == {receivers[u]}"


def test_zero_rainfall_no_change(sim_setup) -> None:
    """Starting from zero depth and zero rain, all depths stay strictly zero."""
    cells, _, cfg, sim = sim_setup
    n = len(cells)

    init_state = SimulationState(
        cells=cells,
        depth_m=np.zeros(n),
        cumulative_infiltrated_m=np.zeros(n),
        cumulative_rainfall_m=np.zeros(n),
    )

    zero_rain = np.zeros(24)
    traj = sim.run(init_state, zero_rain)

    assert np.all(traj.depths_m == 0.0)
    assert np.all(traj.cumulative_infiltrated_m == 0.0)
    assert traj.mass_balance_error() < 1e-12


def test_non_negativity_under_heavy_rain(sim_setup) -> None:
    """Verify water depths remain >= 0 for all cells across all timesteps under heavy rainfall."""
    cells, _, _, sim = sim_setup
    n = len(cells)

    init_state = SimulationState(
        cells=cells,
        depth_m=np.zeros(n),
        cumulative_infiltrated_m=np.zeros(n),
        cumulative_rainfall_m=np.zeros(n),
    )

    # 100 mm/step extreme rainfall for 24 steps
    heavy_rain = np.full(24, 100.0)
    traj = sim.run(init_state, heavy_rain)

    assert np.all(traj.depths_m >= 0.0)
    assert np.all(traj.depths_m <= sim.config.max_depth_m)


def test_mass_balance_closed_domain(sim_setup) -> None:
    """With infiltration disabled, total water in equals total surface water stored."""
    cells, terrain, _, _ = sim_setup
    n = len(cells)

    no_infil_cfg = SimulationConfig(
        manning_n=0.03,
        runoff_coefficient=0.20,
        cfl_safety_factor=0.5,
        infiltration_model="constant",
        default_infiltration_rate_mm_hr=0.0,  # Zero infiltration
    )
    sim = SurfaceFlowSimulator(cells, terrain, no_infil_cfg, timestep_minutes=15)

    init_state = SimulationState(
        cells=cells,
        depth_m=np.zeros(n),
        cumulative_infiltrated_m=np.zeros(n),
        cumulative_rainfall_m=np.zeros(n),
    )

    rain_series = np.array([5.0, 10.0, 15.0, 12.0, 8.0, 4.0, 0.0, 0.0])
    traj = sim.run(init_state, rain_series)

    rel_error = traj.relative_mass_balance_error(runoff_coefficient=0.20)
    assert rel_error < 1e-9, f"Mass balance error too high without infiltration: {rel_error}"


def test_mass_balance_with_infiltration(sim_setup) -> None:
    """With active infiltration, stored surface volume + infiltrated volume equals applied rainfall."""
    cells, _, cfg, sim = sim_setup
    n = len(cells)

    init_state = SimulationState(
        cells=cells,
        depth_m=np.zeros(n),
        cumulative_infiltrated_m=np.zeros(n),
        cumulative_rainfall_m=np.zeros(n),
    )

    rain_series = np.full(24, 15.0)  # 15 mm every 15 mins for 6 hours
    traj = sim.run(init_state, rain_series)

    rel_error = traj.relative_mass_balance_error(runoff_coefficient=cfg.runoff_coefficient)
    assert rel_error < 1e-9, f"Mass balance error too high with infiltration: {rel_error}"


def test_rainfall_increases_depth_monotonically() -> None:
    """Verify that when infiltration=0 and outflow is turned off, depths increase monotonically."""
    cells = create_hex_grid(19.0760, 72.8777, radius_cells=1, resolution=9)
    terrain = generate_synthetic_terrain(cells, seed=42)
    n = len(cells)

    # Infinite Manning roughness (no sheet flow) + 0 infiltration
    static_cfg = SimulationConfig(
        manning_n=1e9,
        runoff_coefficient=0.0,
        default_infiltration_rate_mm_hr=0.0,
        infiltration_model="constant",
    )
    sim = SurfaceFlowSimulator(cells, terrain, static_cfg)

    init_state = SimulationState(
        cells=cells,
        depth_m=np.zeros(n),
        cumulative_infiltrated_m=np.zeros(n),
        cumulative_rainfall_m=np.zeros(n),
    )

    rain = np.array([5.0, 5.0, 5.0, 5.0])
    traj = sim.run(init_state, rain)

    for t in range(len(rain)):
        diff = traj.depths_m[t + 1] - traj.depths_m[t]
        assert np.all(diff >= -1e-12)


def test_sinks_accumulate_water(sim_setup) -> None:
    """Verify that water routed to a terminal sink cell stays there (zero outflow from sinks)."""
    cells, terrain, cfg, sim = sim_setup
    n = len(cells)

    # Identify lowest sink cell
    receivers = compute_d8_receivers(cells, terrain)
    sinks = [c for c, r in receivers.items() if r is None]
    assert len(sinks) >= 1
    sink_idx = sim.cell_to_idx[sinks[0]]

    # Place water only in the sink cell and step with 0 rainfall and 0 infiltration
    no_infil_cfg = SimulationConfig(
        manning_n=0.03,
        runoff_coefficient=0.0,
        default_infiltration_rate_mm_hr=0.0,
        infiltration_model="constant",
    )
    sim_no_infil = SurfaceFlowSimulator(cells, terrain, no_infil_cfg)

    init_depth = np.zeros(n)
    init_depth[sink_idx] = 1.0  # 1 metre of water in sink
    state = SimulationState(
        cells=cells,
        depth_m=init_depth,
        cumulative_infiltrated_m=np.zeros(n),
        cumulative_rainfall_m=np.zeros(n),
    )

    # Advance 5 steps
    for _ in range(5):
        state = sim_no_infil.step(state, rainfall_mm_per_step=0.0)

    # Depth in sink must remain unchanged
    assert abs(state.depth_m[sink_idx] - 1.0) < 1e-9
    # All other cells remain zero
    for i in range(n):
        if i != sink_idx:
            assert state.depth_m[i] == 0.0


def test_state_copy_is_independent(sim_setup) -> None:
    """Verify SimulationState.copy creates completely detached arrays."""
    cells, _, _, _ = sim_setup
    n = len(cells)

    s1 = SimulationState(
        cells=cells,
        depth_m=np.ones(n),
        cumulative_infiltrated_m=np.zeros(n),
        cumulative_rainfall_m=np.zeros(n),
    )
    s2 = s1.copy()

    s2.depth_m[0] = 99.0
    assert s1.depth_m[0] == 1.0


def test_trajectory_save_load_roundtrip(tmp_path: Path, sim_setup) -> None:
    """Verify SimulationTrajectory serialization and deserialization via .npz."""
    cells, _, cfg, sim = sim_setup
    n = len(cells)

    init_state = SimulationState(
        cells=cells,
        depth_m=np.zeros(n),
        cumulative_infiltrated_m=np.zeros(n),
        cumulative_rainfall_m=np.zeros(n),
    )
    traj = sim.run(init_state, np.full(4, 10.0))

    save_file = tmp_path / "test_traj.npz"
    traj.save(save_file)
    assert save_file.exists()

    loaded = SimulationTrajectory.load(save_file)
    assert loaded.cells == traj.cells
    assert loaded.timestep_minutes == traj.timestep_minutes
    np.testing.assert_array_equal(loaded.depths_m, traj.depths_m)
    np.testing.assert_array_equal(loaded.cumulative_infiltrated_m, traj.cumulative_infiltrated_m)


def test_simulator_determinism(sim_setup) -> None:
    """Verify running the simulator twice with identical inputs produces identical trajectories."""
    cells, terrain, cfg, sim = sim_setup
    n = len(cells)

    init1 = SimulationState(
        cells=cells,
        depth_m=np.zeros(n),
        cumulative_infiltrated_m=np.zeros(n),
        cumulative_rainfall_m=np.zeros(n),
    )
    init2 = init1.copy()

    rain = np.array([20.0, 15.0, 10.0, 5.0])
    traj1 = sim.run(init1, rain)
    traj2 = sim.run(init2, rain)

    np.testing.assert_array_equal(traj1.depths_m, traj2.depths_m)
    np.testing.assert_array_equal(traj1.cumulative_infiltrated_m, traj2.cumulative_infiltrated_m)


def test_cfl_cap_prevents_negative_depth(sim_setup) -> None:
    """Verify that even with unrealistic Manning roughness (n = 1e-4), depth remains non-negative."""
    cells, terrain, _, _ = sim_setup
    n = len(cells)

    extreme_cfg = SimulationConfig(
        manning_n=1e-4,  # ultra-low friction -> huge theoretical outflow
        cfl_safety_factor=0.5,
        runoff_coefficient=0.20,
        infiltration_initial_mm_per_hr=0.0,
        infiltration_residual_mm_per_hr=0.0,
    )
    extreme_sim = SurfaceFlowSimulator(cells, terrain, extreme_cfg)

    init_state = SimulationState(
        cells=cells,
        depth_m=np.full(n, 0.5),  # 0.5 m initial depth
        cumulative_infiltrated_m=np.zeros(n),
        cumulative_rainfall_m=np.zeros(n),
    )

    state = extreme_sim.step(init_state, rainfall_mm_per_step=0.0)
    assert np.all(state.depth_m >= 0.0)
    # Check that each cell had at most 50% of its depth drained in one step
    for i in range(n):
        # Even without inflow from upstream, depth could not drop below 0.5 * (1 - cfl_safety_factor) = 0.25
        # With inflow from upstream, it's >= 0.25
        assert state.depth_m[i] >= 0.25 - 1e-6
