"""State representations for the Rapid Terrain-Driven Surface-Flow Simulator."""

from dataclasses import dataclass
from typing import List
import numpy as np


@dataclass
class SimulationState:
    """Snapshot of the physical hydrological state on the H3 cell network at a discrete timestep.

    Attributes:
        cells: Fixed ordered list of N H3 cell IDs.
        depth_m: Surface water depth in metres above ground level, shape (N,), float64, non-negative.
        cumulative_infiltrated_m: Cumulative depth equivalent of water infiltrated, shape (N,), float64.
        cumulative_rainfall_m: Cumulative depth equivalent of gross rainfall applied, shape (N,), float64.
        time_step: Discrete integer timestep index (t = 0, 1, 2, ...).
    """

    cells: List[str]
    depth_m: np.ndarray
    cumulative_infiltrated_m: np.ndarray
    cumulative_rainfall_m: np.ndarray
    time_step: int = 0

    def __post_init__(self) -> None:
        """Validate shape consistency, float64 precision, and non-negativity."""
        n = len(self.cells)
        if not isinstance(self.depth_m, np.ndarray):
            self.depth_m = np.asarray(self.depth_m, dtype=np.float64)
        else:
            self.depth_m = self.depth_m.astype(np.float64, copy=False)

        if not isinstance(self.cumulative_infiltrated_m, np.ndarray):
            self.cumulative_infiltrated_m = np.asarray(self.cumulative_infiltrated_m, dtype=np.float64)
        else:
            self.cumulative_infiltrated_m = self.cumulative_infiltrated_m.astype(np.float64, copy=False)

        if not isinstance(self.cumulative_rainfall_m, np.ndarray):
            self.cumulative_rainfall_m = np.asarray(self.cumulative_rainfall_m, dtype=np.float64)
        else:
            self.cumulative_rainfall_m = self.cumulative_rainfall_m.astype(np.float64, copy=False)

        if self.depth_m.shape != (n,):
            raise ValueError(f"depth_m shape {self.depth_m.shape} does not match cell count {n}")
        if self.cumulative_infiltrated_m.shape != (n,):
            raise ValueError(
                f"cumulative_infiltrated_m shape {self.cumulative_infiltrated_m.shape} != {n}"
            )
        if self.cumulative_rainfall_m.shape != (n,):
            raise ValueError(
                f"cumulative_rainfall_m shape {self.cumulative_rainfall_m.shape} != {n}"
            )

        if np.any(self.depth_m < -1e-9):
            min_val = float(np.min(self.depth_m))
            raise ValueError(f"Negative water depth detected in SimulationState: min={min_val}")

        # Clean numerical micro-precision underflows
        self.depth_m = np.maximum(self.depth_m, 0.0)

    def total_volume_m3(self, areas_m2: np.ndarray) -> float:
        """Calculate total surface water volume currently stored across all cells in m^3."""
        if areas_m2.shape != self.depth_m.shape:
            raise ValueError(f"areas_m2 shape {areas_m2.shape} must match depth shape {self.depth_m.shape}")
        return float(np.sum(self.depth_m * areas_m2))

    def copy(self) -> "SimulationState":
        """Return a deep, independent copy of the current state."""
        return SimulationState(
            cells=list(self.cells),
            depth_m=self.depth_m.copy(),
            cumulative_infiltrated_m=self.cumulative_infiltrated_m.copy(),
            cumulative_rainfall_m=self.cumulative_rainfall_m.copy(),
            time_step=self.time_step,
        )
