"""Simulation trajectory storage and mass balance audit for the Rapid Surface-Flow Simulator."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
import numpy as np


@dataclass
class SimulationTrajectory:
    """Complete temporal record of an executed surface-flow simulation.

    Attributes:
        cells: Deterministic list of N H3 cell IDs.
        timestep_minutes: Discrete simulation timestep interval in minutes.
        depths_m: Surface water depth evolution array of shape (T + 1, N), including t=0 initial state.
        rainfall_mm: Rainfall series applied per step of shape (T, N) or (T,).
        cumulative_infiltrated_m: Infiltration evolution array of shape (T + 1, N).
        areas_m2: Fixed surface area of each cell in m^2, shape (N,).
    """

    cells: List[str]
    timestep_minutes: int
    depths_m: np.ndarray
    rainfall_mm: np.ndarray
    cumulative_infiltrated_m: np.ndarray
    areas_m2: np.ndarray

    def mass_balance_error(self, areas_m2: np.ndarray, runoff_coefficient: float = 0.20) -> float:
        """Compute closed-domain mass conservation balance error in cubic metres (m^3).

        For a closed system without external boundary drainage:
            V_initial + V_rain_applied = V_final_stored + V_total_infiltrated + Error

        Where:
            V_initial = sum_i(d_i(0) * A_i)
            V_final   = sum_i(d_i(T) * A_i)
            V_rain_applied = sum_t( sum_i( (P_i(t) / 1000.0) * (1.0 - runoff_coefficient) * A_i ) )
            V_infiltrated  = sum_i( cumulative_infiltrated_m(T) * A_i )

        Args:
            areas_m2: Fixed surface area of each cell in m^2, shape (N,). Required.
            runoff_coefficient: Runoff reduction fraction (default 0.20).

        Returns:
            float: Absolute discrepancy in m^3: |(V_initial + V_rain_applied) - (V_final + V_infiltrated)|.
        """
        areas = np.asarray(areas_m2, dtype=np.float64)
        if areas.shape != (len(self.cells),):
            raise ValueError(f"areas_m2 shape {areas.shape} must match cells length {len(self.cells)}")

        # 1. Surface water volumes
        v_initial = float(np.sum(self.depths_m[0] * areas))
        v_final = float(np.sum(self.depths_m[-1] * areas))

        # 2. Cumulative infiltration volume
        v_infiltrated = float(np.sum(self.cumulative_infiltrated_m[-1] * areas))

        # 3. Applied net rainfall volume across all steps
        # rainfall_mm can be shape (T, N) or (T,)
        if self.rainfall_mm.ndim == 1:
            # (T,) scalar per timestep broadcasted over all cells
            total_rain_depth_m = float(np.sum(self.rainfall_mm)) / 1000.0
            v_rain_applied = total_rain_depth_m * (1.0 - runoff_coefficient) * float(np.sum(areas))
        else:
            # (T, N) spatially variable rainfall
            rain_m = (self.rainfall_mm / 1000.0) * (1.0 - runoff_coefficient)  # shape (T, N)
            v_rain_applied = float(np.sum(rain_m * areas))

        expected_total = v_initial + v_rain_applied
        actual_total = v_final + v_infiltrated

        return float(abs(expected_total - actual_total))

    def relative_mass_balance_error(self, areas_m2: np.ndarray, runoff_coefficient: float = 0.20) -> float:
        """Compute relative mass balance discrepancy normalized by total water entering system."""
        areas = np.asarray(areas_m2, dtype=np.float64)
        abs_err = self.mass_balance_error(areas_m2=areas, runoff_coefficient=runoff_coefficient)
        v_initial = float(np.sum(self.depths_m[0] * areas))

        if self.rainfall_mm.ndim == 1:
            total_rain_depth_m = float(np.sum(self.rainfall_mm)) / 1000.0
            v_rain = total_rain_depth_m * (1.0 - runoff_coefficient) * float(np.sum(areas))
        else:
            rain_m = (self.rainfall_mm / 1000.0) * (1.0 - runoff_coefficient)
            v_rain = float(np.sum(rain_m * areas))

        total_water = v_initial + v_rain
        if total_water < 1e-9:
            return 0.0
        return float(abs_err / total_water)

    def save(self, path: Union[str, Path]) -> None:
        """Serialize trajectory arrays to a compressed NumPy .npz file."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        np.savez_compressed(
            file_path,
            cells=np.array(self.cells, dtype=object),
            timestep_minutes=np.array([self.timestep_minutes]),
            depths_m=self.depths_m,
            rainfall_mm=self.rainfall_mm,
            cumulative_infiltrated_m=self.cumulative_infiltrated_m,
            areas_m2=self.areas_m2,
        )

    @classmethod
    def load(cls, path: Union[str, Path]) -> "SimulationTrajectory":
        """Load and reconstruct a SimulationTrajectory from a .npz file."""
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Trajectory file not found: {file_path}")

        with np.load(file_path, allow_pickle=True) as data:
            cells = [str(c) for c in data["cells"]]
            timestep_minutes = int(data["timestep_minutes"][0])
            depths_m = data["depths_m"]
            rainfall_mm = data["rainfall_mm"]
            cumulative_infiltrated_m = data["cumulative_infiltrated_m"]
            areas_m2 = data["areas_m2"]

        return cls(
            cells=cells,
            timestep_minutes=timestep_minutes,
            depths_m=depths_m,
            rainfall_mm=rainfall_mm,
            cumulative_infiltrated_m=cumulative_infiltrated_m,
            areas_m2=areas_m2,
        )
