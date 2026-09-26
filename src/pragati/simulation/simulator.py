"""Rapid Terrain-Driven Surface-Flow Simulator.

An explicit-time-step, finite-volume surface water routing model on discrete H3 grids.
Uses single-receiver D8 downhill routing, kinematic/Manning sheet flow, and infiltration.

Scientific and architectural constraints:
- Simulator terminology: "Rapid Terrain-Driven Surface-Flow Simulator".
- Not a full 2D hydraulic solver; designed for rapid surrogate generation and refinement.
- Exact volumetric continuity: ΔV_i = P_i + I_i − O_i − F_i.
"""

import math
from typing import Dict, List, Optional, Union
import numpy as np

from pragati.config import SimulationConfig
from pragati.graph.h3_utils import cell_area_m2
from pragati.simulation.routing import compute_d8_receivers, compute_reverse_routing
from pragati.simulation.state import SimulationState
from pragati.simulation.trajectory import SimulationTrajectory


class SurfaceFlowSimulator:
    """Rapid Terrain-Driven Surface-Flow Simulator for the PRAGATI research framework."""

    def __init__(
        self,
        cells: List[str],
        terrain: Dict[str, Dict[str, float]],
        config: SimulationConfig,
        timestep_minutes: int = 15,
    ) -> None:
        """Initialize the simulator topology, geometry, and physical parameters.

        Args:
            cells: Deterministically ordered list of N H3 cell IDs.
            terrain: Topographic attributes dictionary per cell.
            config: Simulation physical parameters configuration.
            timestep_minutes: Discrete simulation timestep interval in minutes (default 15).
        """
        self.cells = list(cells)
        self.terrain = terrain
        self.config = config
        self.timestep_minutes = timestep_minutes
        self.dt_seconds = float(timestep_minutes * 60.0)

        self.n = len(cells)
        self.cell_to_idx = {c: i for i, c in enumerate(cells)}

        # Precompute D8 receivers and reverse upstream contributors
        self.receivers_dict = compute_d8_receivers(cells, terrain)
        self.upstreams_dict = compute_reverse_routing(cells, self.receivers_dict)

        # Vectorized receiver indices (-1 for sinks)
        self.receiver_indices = np.full(self.n, -1, dtype=np.int64)
        for i, c in enumerate(cells):
            rec = self.receivers_dict.get(c)
            if rec is not None and rec in self.cell_to_idx:
                self.receiver_indices[i] = self.cell_to_idx[rec]

        # Geometry arrays: Area (A_i), effective flow width (W_i), slope (S_i)
        self.areas_m2 = np.zeros(self.n, dtype=np.float64)
        self.widths_m = np.zeros(self.n, dtype=np.float64)
        self.slopes = np.zeros(self.n, dtype=np.float64)

        for i, c in enumerate(cells):
            # 1. Surface area
            area = cell_area_m2(c) if c in terrain else self.config.cell_area_sqm
            self.areas_m2[i] = area

            # 2. Flow width: For a regular hexagon of area A, edge length w = sqrt(2 * A / (3 * sqrt(3)))
            edge_len = math.sqrt(2.0 * area / (3.0 * math.sqrt(3.0)))
            self.widths_m[i] = edge_len

            # 3. Dimensionless slope: sin(slope_deg)
            slope_deg = float(terrain[c].get("slope_deg", 0.0))
            slope_rad = math.radians(slope_deg)
            self.slopes[i] = max(1e-4, math.sin(slope_rad))

    def step(
        self, state: SimulationState, rainfall_mm_per_step: Union[np.ndarray, float]
    ) -> SimulationState:
        """Advance the physical hydrological state by one discrete timestep (dt = 15 minutes).

        Conservation order of operations:
            1. Apply net rainfall: d += P_eff / 1000.0, where P_eff = P * (1.0 - runoff_coefficient)
            2. Infiltration: compute potential infiltration depth for current time, take min(d, potential),
               subtract from surface depth and add to cumulative infiltrated.
            3. Outflow: Manning sheet flow with CFL safety factor cap (at most cfl_factor * d * A removed).
            4. Mass routing: remove outflow volume from source cell, transfer strictly to D8 receiver.
            5. Sinks: cells with receiver_indices == -1 retain their water (outflow = 0).
            6. Physical clamp: d = min(d, max_depth_m).

        Args:
            state: Current SimulationState (never mutated).
            rainfall_mm_per_step: Gross rainfall in mm for current step, shape (N,) or scalar float.

        Returns:
            SimulationState: New, independent hydrological state at step t + 1.
        """
        # Broadcast rainfall array to shape (N,)
        if np.isscalar(rainfall_mm_per_step):
            rain_mm = np.full(self.n, float(rainfall_mm_per_step), dtype=np.float64)
        else:
            rain_mm = np.asarray(rainfall_mm_per_step, dtype=np.float64)
            if rain_mm.shape != (self.n,):
                rain_mm = np.broadcast_to(rain_mm, (self.n,)).copy()

        d = state.depth_m.copy()
        cum_infil = state.cumulative_infiltrated_m.copy()
        cum_rain = state.cumulative_rainfall_m.copy()

        # Step 1: Gross rainfall tracking and net rainfall addition
        gross_rain_m = rain_mm / 1000.0
        cum_rain += gross_rain_m

        net_rain_m = gross_rain_m * (1.0 - self.config.runoff_coefficient)
        d += net_rain_m

        # Step 2: Infiltration (Horton exponential decay or constant rate)
        current_time_hr = state.time_step * (self.timestep_minutes / 60.0)
        dt_hr = self.timestep_minutes / 60.0

        if self.config.infiltration_model == "constant":
            infil_rate_mm_hr = self.config.default_infiltration_rate_mm_hr
        else:
            # Horton formula: f(t) = f_residual + (f_initial - f_residual) * exp(-k * t)
            f_res = self.config.infiltration_residual_mm_per_hr
            f_init = self.config.infiltration_initial_mm_per_hr
            k = self.config.infiltration_decay_constant_hr
            infil_rate_mm_hr = f_res + (f_init - f_res) * math.exp(-k * current_time_hr)

        potential_infil_m = (infil_rate_mm_hr * dt_hr) / 1000.0

        # Infiltration cannot exceed available surface water depth
        actual_infil_m = np.minimum(d, potential_infil_m)
        d -= actual_infil_m
        cum_infil += actual_infil_m

        # Step 3 & 4: Outflow computation and D8 routing
        # Manning sheet flow formula: q_i = (1 / n) * W_i * sqrt(S_i) * d_i^(5/3) [m^3 / s]
        # Potential outflow volume: V_out = q_i * dt_seconds
        v_out = np.zeros(self.n, dtype=np.float64)

        has_water = d > 1e-6
        # Only compute Manning flow for non-sink cells with positive depth
        active_flow = has_water & (self.receiver_indices >= 0)

        if np.any(active_flow):
            n_rough = self.config.manning_n
            w = self.widths_m[active_flow]
            s = self.slopes[active_flow]
            d_act = d[active_flow]
            a = self.areas_m2[active_flow]

            # q = (1/n) * W * sqrt(S) * d^(5/3)
            q = (1.0 / n_rough) * w * np.sqrt(s) * (d_act ** (5.0 / 3.0))
            v_potential = q * self.dt_seconds

            # CFL stability cap: at most cfl_factor * d * A
            v_cfl_max = self.config.cfl_safety_factor * d_act * a
            v_out_act = np.minimum(v_potential, v_cfl_max)
            v_out[active_flow] = v_out_act

        # Remove outflow volume from source cells
        d -= v_out / self.areas_m2

        # Step 5: Transfer outflow volume to D8 receivers
        # Use np.add.at for unbuffered accumulation when multiple cells drain into same receiver
        has_transfer = v_out > 0.0
        if np.any(has_transfer):
            transfer_v = v_out[has_transfer]
            target_idxs = self.receiver_indices[has_transfer]

            # Influx depth added to receiver = V_out / A_receiver
            depth_influx = transfer_v / self.areas_m2[target_idxs]
            np.add.at(d, target_idxs, depth_influx)

        # Step 6: Physical constraints
        d = np.clip(d, 0.0, self.config.max_depth_m)

        return SimulationState(
            cells=list(self.cells),
            depth_m=d,
            cumulative_infiltrated_m=cum_infil,
            cumulative_rainfall_m=cum_rain,
            time_step=state.time_step + 1,
        )

    def run(
        self,
        initial_state: SimulationState,
        rainfall_series_mm: np.ndarray,
        num_steps: Optional[int] = None,
    ) -> SimulationTrajectory:
        """Run an end-to-end multi-step simulation trajectory.

        Args:
            initial_state: Hydrological state at t = 0.
            rainfall_series_mm: Array of gross rainfall depths in mm per step.
                Can be shape (T, N) or (T,) for spatially uniform rainfall.
            num_steps: Number of timesteps to simulate. If None, inferred from rainfall_series_mm.

        Returns:
            SimulationTrajectory: Trajectory container recording depths, rainfall, and infiltration.
        """
        rain_arr = np.asarray(rainfall_series_mm, dtype=np.float64)
        total_steps = len(rain_arr) if num_steps is None else num_steps

        # Preallocate history buffers: shape (total_steps + 1, N)
        depths_history = np.zeros((total_steps + 1, self.n), dtype=np.float64)
        infil_history = np.zeros((total_steps + 1, self.n), dtype=np.float64)

        # Record t=0 initial state
        depths_history[0] = initial_state.depth_m
        infil_history[0] = initial_state.cumulative_infiltrated_m

        current_state = initial_state.copy()

        for t in range(total_steps):
            rain_step = rain_arr[t] if rain_arr.ndim == 1 else rain_arr[t]
            current_state = self.step(current_state, rain_step)

            depths_history[t + 1] = current_state.depth_m
            infil_history[t + 1] = current_state.cumulative_infiltrated_m

        return SimulationTrajectory(
            cells=list(self.cells),
            timestep_minutes=self.timestep_minutes,
            depths_m=depths_history,
            rainfall_mm=rain_arr[:total_steps],
            cumulative_infiltrated_m=infil_history,
            areas_m2=self.areas_m2.copy(),
        )
