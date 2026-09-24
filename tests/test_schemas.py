"""Unit tests for Pydantic v2 data schemas in pragati.data.schemas."""

from datetime import datetime
import pytest
from pydantic import ValidationError
from pragati.data.schemas import (
    ObservationWindow,
    SensorQualityFlags,
    SensorReading,
)


def test_sensor_reading_valid() -> None:
    """Verify valid sensor reading construction."""
    reading = SensorReading(
        device_id="node-mumbai-01",
        timestamp=datetime(2026, 7, 26, 14, 0, 0),
        latitude=19.0760,
        longitude=72.8777,
        water_depth_m=0.35,
        rainfall_mm=12.4,
        quality_score=0.95,
    )
    assert reading.device_id == "node-mumbai-01"
    assert reading.water_depth_m == 0.35
    assert reading.quality_score == 0.95


@pytest.mark.parametrize(
    "lat,lon,depth,rain,qual",
    [
        (-1.0, 72.8, 0.5, 10.0, 0.9),      # latitude < 0
        (91.0, 72.8, 0.5, 10.0, 0.9),      # latitude > 90
        (19.0, -181.0, 0.5, 10.0, 0.9),    # lon < -180
        (19.0, 181.0, 0.5, 10.0, 0.9),     # lon > 180
        (19.0, 72.8, -0.1, 10.0, 0.9),     # water depth < 0
        (19.0, 72.8, 0.5, -1.0, 0.9),      # rainfall < 0
        (19.0, 72.8, 0.5, 10.0, -0.01),    # quality score < 0
        (19.0, 72.8, 0.5, 10.0, 1.05),     # quality score > 1
    ],
)
def test_sensor_reading_boundary_rejections(
    lat: float, lon: float, depth: float, rain: float, qual: float
) -> None:
    """Verify boundary condition rejections on SensorReading."""
    with pytest.raises(ValidationError):
        SensorReading(
            device_id="node-01",
            timestamp=datetime.now(),
            latitude=lat,
            longitude=lon,
            water_depth_m=depth,
            rainfall_mm=rain,
            quality_score=qual,
        )


def test_sensor_quality_flags_valid_and_bounds() -> None:
    """Verify SensorQualityFlags validation."""
    flags = SensorQualityFlags(
        missingness=0.05,
        stale=False,
        out_of_range=False,
        spike=False,
        connectivity=0.98,
    )
    assert flags.connectivity == 0.98

    with pytest.raises(ValidationError):
        SensorQualityFlags(
            missingness=1.2,
            stale=False,
            out_of_range=False,
            spike=False,
            connectivity=0.9,
        )

    with pytest.raises(ValidationError):
        SensorQualityFlags(
            missingness=0.1,
            stale=False,
            out_of_range=False,
            spike=False,
            connectivity=-0.1,
        )


def test_observation_window_valid() -> None:
    """Verify valid ObservationWindow creation."""
    win = ObservationWindow(
        h3_cell="8960e227097ffff",
        start_time=datetime(2026, 7, 26, 12, 0, 0),
        timestep_minutes=15,
        depth_series=[0.1, 0.15, 0.2, 0.25],
        rainfall_series=[2.0, 5.0, 8.0, 10.0],
        quality_series=[1.0, 1.0, 0.9, 0.9],
    )
    assert len(win.depth_series) == 4
    assert win.timestep_minutes == 15


def test_observation_window_invalid_timesteps() -> None:
    """Verify timestep_minutes must be one of {5, 10, 15, 30, 60}."""
    with pytest.raises(ValidationError):
        ObservationWindow(
            h3_cell="8960e227097ffff",
            start_time=datetime.now(),
            timestep_minutes=25,  # Invalid interval
            depth_series=[0.1],
            rainfall_series=[1.0],
            quality_series=[1.0],
        )


def test_observation_window_series_length_mismatch() -> None:
    """Verify mismatched series lengths raise validation errors."""
    with pytest.raises(ValidationError):
        ObservationWindow(
            h3_cell="8960e227097ffff",
            start_time=datetime.now(),
            timestep_minutes=15,
            depth_series=[0.1, 0.2, 0.3],
            rainfall_series=[1.0, 2.0],  # only 2 elements
            quality_series=[1.0, 1.0, 1.0],
        )


def test_observation_window_series_bounds() -> None:
    """Verify series values cannot be negative or out of [0, 1] range."""
    with pytest.raises(ValidationError):
        ObservationWindow(
            h3_cell="8960e227097ffff",
            start_time=datetime.now(),
            timestep_minutes=15,
            depth_series=[-0.1],  # negative depth
            rainfall_series=[1.0],
            quality_series=[0.8],
        )

    with pytest.raises(ValidationError):
        ObservationWindow(
            h3_cell="8960e227097ffff",
            start_time=datetime.now(),
            timestep_minutes=15,
            depth_series=[0.1],
            rainfall_series=[1.0],
            quality_series=[1.5],  # quality > 1.0
        )
