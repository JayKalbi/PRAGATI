"""Unit tests for PRAGATI configuration and timestep calculations."""

from pathlib import Path
import pytest
from pragati.config import (
    AetherConfig,
    GraphConfig,
    ModelConfig,
    PragatiConfig,
    SimulationConfig,
    SpatialConfig,
    TemporalConfig,
)


def test_default_config_values() -> None:
    """Verify that default settings match the frozen PRAGATI scientific baseline."""
    config = PragatiConfig()

    # Spatial resolution
    assert config.spatial.h3_resolution == 9

    # Temporal parameters
    assert config.temporal.timestep_minutes == 15
    assert config.temporal.lookback_hours == 6.0
    assert config.temporal.forecast_horizons_hours == [2.0, 4.0, 6.0]

    # Target
    assert config.target.name == "inundation_depth"
    assert config.target.unit == "metres"
    assert config.target.reference_level == "local_ground"

    # Model architecture
    assert config.model.name == "PG-STGNN"
    assert config.model.spatial_encoder == "GraphSAGE"
    assert config.model.temporal_encoder == "GRU"
    assert config.model.hidden_dim == 64
    assert config.model.latent_embedding_dim == 64
    assert config.model.ensemble_size == 3
    assert len(config.model.random_seeds) == 3

    # Graph edge attributes
    assert "elevation_diff" in config.graph.edge_attributes
    assert "slope" in config.graph.edge_attributes
    assert "flow_direction_compatibility" in config.graph.edge_attributes
    assert "flow_accumulation" in config.graph.edge_attributes
    assert "distance" in config.graph.edge_attributes

    # AETHER thresholds
    assert config.aether.ood_mahalanobis_threshold == 3.0
    assert config.aether.ensemble_variance_threshold == 0.04
    assert config.aether.min_sensor_quality_score == 0.70
    assert config.aether.physics_residual_threshold == 0.05


def test_horizon_to_timestep_calculations() -> None:
    """Verify exact lookback and horizon-to-timestep conversions for frozen baseline."""
    temporal = TemporalConfig(
        timestep_minutes=15,
        lookback_hours=6.0,
        forecast_horizons_hours=[2.0, 4.0, 6.0],
    )

    # 6.0 hours * 60 mins/hr / 15 mins/step = 24 timesteps
    assert temporal.lookback_timesteps == 24

    # 2h -> 8 steps, 4h -> 16 steps, 6h -> 24 steps
    assert temporal.horizon_timesteps == [8, 16, 24]


def test_custom_temporal_calculations() -> None:
    """Verify timestep calculation behavior with custom temporal configurations."""
    custom_temp = TemporalConfig(
        timestep_minutes=30,
        lookback_hours=3.0,
        forecast_horizons_hours=[1.0, 2.0],
    )
    # 3h * 60 / 30 = 6 timesteps
    assert custom_temp.lookback_timesteps == 6
    # 1h -> 2 steps, 2h -> 4 steps
    assert custom_temp.horizon_timesteps == [2, 4]


def test_invalid_horizon_ordering() -> None:
    """Ensure non-ascending or empty horizons raise validation errors."""
    with pytest.raises(ValueError):
        TemporalConfig(forecast_horizons_hours=[6.0, 2.0])

    with pytest.raises(ValueError):
        TemporalConfig(forecast_horizons_hours=[])


def test_ensemble_seeds_validation() -> None:
    """Ensure at least as many seeds as ensemble_size are configured."""
    with pytest.raises(ValueError):
        ModelConfig(ensemble_size=4, random_seeds=[42, 1337])


def test_yaml_roundtrip(tmp_path: Path) -> None:
    """Verify that configuration can be saved to and loaded from YAML seamlessly."""
    config = PragatiConfig()
    yaml_file = tmp_path / "test_config.yaml"

    config.to_yaml(yaml_file)
    assert yaml_file.exists()

    loaded_config = PragatiConfig.from_yaml(yaml_file)
    assert loaded_config.spatial.h3_resolution == config.spatial.h3_resolution
    assert loaded_config.temporal.lookback_timesteps == config.temporal.lookback_timesteps
    assert loaded_config.temporal.horizon_timesteps == config.temporal.horizon_timesteps
    assert loaded_config.model.name == config.model.name


def test_load_repository_baseline_yaml() -> None:
    """Verify that configs/baseline_config.yaml loads properly and matches defaults."""
    repo_yaml = Path(__file__).resolve().parent.parent / "configs" / "baseline_config.yaml"
    assert repo_yaml.is_file(), f"baseline_config.yaml not found at {repo_yaml}"

    config = PragatiConfig.from_yaml(repo_yaml)
    assert config.spatial.h3_resolution == 9
    assert config.temporal.lookback_timesteps == 24
    assert config.temporal.horizon_timesteps == [8, 16, 24]
    assert config.graph.mode == "terrain_aware"
    assert config.graph.direction_policy == "downhill"
    assert config.graph.use_edge_attr is True


def test_graph_config_defaults() -> None:
    """Verify default graph configuration settings for frozen baseline."""
    graph_cfg = GraphConfig()
    assert graph_cfg.mode == "terrain_aware"
    assert graph_cfg.direction_policy == "downhill"
    assert graph_cfg.use_edge_attr is True
    assert "elevation" in graph_cfg.node_features
    assert "flow_accumulation" in graph_cfg.node_features
    assert len(graph_cfg.edge_attributes) == 5


def test_graph_config_ablation_settings() -> None:
    """Verify RQ1 ablation flat graph configuration initialization."""
    flat_cfg = GraphConfig(
        mode="flat",
        direction_policy="bidirectional",
        use_edge_attr=False,
    )
    assert flat_cfg.mode == "flat"
    assert flat_cfg.direction_policy == "bidirectional"
    assert flat_cfg.use_edge_attr is False


def test_simulation_config_defaults() -> None:
    """Verify default simulation parameters match frozen baseline physics specifications."""
    sim_cfg = SimulationConfig()
    assert sim_cfg.manning_n == 0.03
    assert sim_cfg.runoff_coefficient == 0.20
    assert sim_cfg.cfl_safety_factor == 0.5
    assert sim_cfg.infiltration_model == "exponential_decay"
    assert sim_cfg.infiltration_initial_mm_per_hr == 20.0
    assert sim_cfg.infiltration_residual_mm_per_hr == 2.0
    assert sim_cfg.infiltration_decay_constant_hr == 1.0
    assert sim_cfg.max_depth_m == 5.0
    assert sim_cfg.cell_area_sqm == 10000.0


def test_simulation_config_custom_values() -> None:
    """Verify custom configuration overrides for constant infiltration or alternate roughness."""
    sim_cfg = SimulationConfig(
        manning_n=0.04,
        infiltration_model="constant",
        default_infiltration_rate_mm_hr=10.0,
        cfl_safety_factor=0.3,
    )
    assert sim_cfg.manning_n == 0.04
    assert sim_cfg.infiltration_model == "constant"
    assert sim_cfg.default_infiltration_rate_mm_hr == 10.0
    assert sim_cfg.cfl_safety_factor == 0.3


