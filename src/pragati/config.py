"""Configuration management for the PRAGATI research framework.

Validates and manages frozen baseline settings including spatial resolution,
temporal lookback/horizons, graph parameters, neural architecture, and AETHER thresholds.
"""

from pathlib import Path
from typing import Any, Dict, List, Literal
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class SpatialConfig(BaseModel):
    """Spatial configuration parameters based on Uber H3 discrete global grid."""

    h3_resolution: int = Field(
        default=9,
        ge=0,
        le=15,
        description="H3 spatial resolution (frozen baseline: 9, approx 0.1 km2/cell).",
    )


class TemporalConfig(BaseModel):
    """Temporal configuration and multi-horizon horizon conversions."""

    timestep_minutes: int = Field(
        default=15,
        gt=0,
        description="Discrete time step in minutes (frozen baseline: 15 mins).",
    )
    lookback_hours: float = Field(
        default=6.0,
        gt=0.0,
        description="Lookback history window in hours (frozen baseline: 6.0 hours).",
    )
    forecast_horizons_hours: List[float] = Field(
        default_factory=lambda: [2.0, 4.0, 6.0],
        description="Forecast horizon offsets in hours (frozen baseline: 2h, 4h, 6h).",
    )

    @field_validator("forecast_horizons_hours")
    @classmethod
    def validate_horizons(cls, horizons: List[float]) -> List[float]:
        """Ensure horizons are positive and monotonically increasing."""
        if not horizons:
            raise ValueError("forecast_horizons_hours cannot be empty.")
        for h in horizons:
            if h <= 0:
                raise ValueError(f"Forecast horizon must be positive: {h}")
        if horizons != sorted(horizons):
            raise ValueError("forecast_horizons_hours must be sorted in ascending order.")
        return horizons

    @property
    def lookback_timesteps(self) -> int:
        """Calculate number of input sequence timesteps.

        For 6.0 hours lookback with 15-minute intervals: 6.0 * 60 / 15 = 24 timesteps.
        """
        return int(round((self.lookback_hours * 60.0) / self.timestep_minutes))

    @property
    def horizon_timesteps(self) -> List[int]:
        """Calculate list of future horizon timesteps.

        For [2.0, 4.0, 6.0] hours with 15-minute intervals: [8, 16, 24] timesteps.
        """
        return [
            int(round((h * 60.0) / self.timestep_minutes))
            for h in self.forecast_horizons_hours
        ]


class TargetConfig(BaseModel):
    """Target variable specification."""

    name: str = "inundation_depth"
    unit: str = "metres"
    reference_level: str = "local_ground"


class GraphConfig(BaseModel):
    """Topological and terrain-aware edge configuration.

    Note:
        The combination of mode='flat' and use_edge_attr=False serves as the
        established flat-graph baseline for RQ1 ablation.
    """

    # Graph mode: 'terrain_aware' incorporates D8 attributes; 'flat' strips terrain edges (RQ1 baseline)
    mode: Literal["terrain_aware", "flat"] = "terrain_aware"
    # Direction policy: 'downhill' filters edges to strictly downhill flow; 'bidirectional' retains both
    direction_policy: Literal["downhill", "bidirectional"] = "downhill"
    directed: bool = True
    max_neighbors: int = 6
    # Whether to construct and attach edge_attr tensor to PyG Data object (False for RQ1 flat baseline)
    use_edge_attr: bool = True
    node_features: List[str] = Field(
        default_factory=lambda: [
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
    )
    edge_attributes: List[str] = Field(
        default_factory=lambda: [
            "elevation_diff",
            "slope",
            "flow_direction_compatibility",
            "flow_accumulation",
            "distance",
        ]
    )


class LossConfig(BaseModel):
    """Multi-objective loss regularization weights."""

    lambda_continuity: float = Field(
        default=0.1, ge=0.0, description="Continuity-inspired physics regularizer weight."
    )
    lambda_spatial: float = Field(
        default=0.05, ge=0.0, description="Spatial smoothness loss weight."
    )
    lambda_temporal: float = Field(
        default=0.05, ge=0.0, description="Temporal consistency loss weight."
    )


class ModelConfig(BaseModel):
    """Neural network architecture configuration for PG-STGNN."""

    name: str = "PG-STGNN"
    spatial_encoder: Literal["GraphSAGE", "GCN", "GAT"] = "GraphSAGE"
    temporal_encoder: Literal["GRU", "LSTM", "RNN"] = "GRU"
    hidden_dim: int = 64
    latent_embedding_dim: int = 64
    ensemble_size: int = Field(
        default=3,
        ge=1,
        description="Number of independently seeded models for ensemble disagreement.",
    )
    random_seeds: List[int] = Field(default_factory=lambda: [42, 1337, 2026])
    loss: LossConfig = Field(default_factory=LossConfig)

    @model_validator(mode="after")
    def verify_seeds_match_ensemble_size(self) -> "ModelConfig":
        """Verify that enough seeds are provided for the ensemble."""
        if len(self.random_seeds) < self.ensemble_size:
            raise ValueError(
                f"Number of random seeds ({len(self.random_seeds)}) must be >= "
                f"ensemble_size ({self.ensemble_size})."
            )
        return self


class AetherConfig(BaseModel):
    """AETHER reliability and trust gate thresholds and placeholders."""

    ood_mahalanobis_threshold: float = Field(
        default=3.0,
        gt=0.0,
        description="Threshold on Mahalanobis distance D_M in 64-dim latent embedding space.",
    )
    ensemble_variance_threshold: float = Field(
        default=0.04,
        gt=0.0,
        description="Threshold on forecast variance across ensemble members.",
    )
    min_sensor_quality_score: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Minimum admissible sensor quality metric q before flagging corruption.",
    )
    physics_residual_threshold: float = Field(
        default=0.05,
        gt=0.0,
        description="Admissible continuity residual error before triggering Refine/Abstain.",
    )


class SimulationConfig(BaseModel):
    """Rapid Terrain-Driven Surface-Flow Simulator parameters.

    Physical model parameters for explicit finite-volume surface water routing on the H3 grid.
    """

    name: str = "Rapid Terrain-Driven Surface-Flow Simulator"
    cell_area_sqm: float = Field(
        default=10000.0,
        description=(
            "Nominal fallback cell area in m^2. NOTE: The simulator uses "
            "pragati.graph.h3_utils.cell_area_m2(cell) for the true per-cell H3 "
            "surface area; this field is retained only as a reference value for "
            "documentation and future grid-agnostic code paths."
        ),
    )
    default_infiltration_rate_mm_hr: float = 5.0
    manning_n: float = Field(
        default=0.03, gt=0.0, description="Manning roughness coefficient for overland sheet flow."
    )
    runoff_coefficient: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Fraction of rainfall lost to initial depression/retention before overland flow.",
    )
    cfl_safety_factor: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description="Maximum fraction of cell water volume allowable for outflow in a single time step.",
    )
    infiltration_model: Literal["constant", "exponential_decay"] = "exponential_decay"
    infiltration_initial_mm_per_hr: float = Field(
        default=20.0, ge=0.0, description="Initial potential infiltration rate in Horton-style decay."
    )
    infiltration_residual_mm_per_hr: float = Field(
        default=2.0, ge=0.0, description="Asymptotic saturated infiltration rate in Horton-style decay."
    )
    infiltration_decay_constant_hr: float = Field(
        default=1.0, gt=0.0, description="Horton infiltration decay constant (in hours)."
    )
    max_depth_m: float = Field(
        default=5.0, gt=0.0, description="Physical upper ceiling clamp for surface inundation depth in metres."
    )


class PragatiConfig(BaseModel):
    """Master configuration container for PRAGATI."""

    spatial: SpatialConfig = Field(default_factory=SpatialConfig)
    temporal: TemporalConfig = Field(default_factory=TemporalConfig)
    target: TargetConfig = Field(default_factory=TargetConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    aether: AetherConfig = Field(default_factory=AetherConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PragatiConfig":
        """Load and validate configuration from a YAML file."""
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            raw_dict = yaml.safe_load(f) or {}
        return cls(**raw_dict)

    def to_yaml(self, path: str | Path) -> None:
        """Serialize configuration to a YAML file."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)
