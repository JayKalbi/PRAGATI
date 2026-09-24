"""Pydantic v2 data schemas for telemetry, sensor quality flags, and observation windows."""

from datetime import datetime
from typing import List, Set
from pydantic import BaseModel, Field, field_validator, model_validator

VALID_TIMESTEPS: Set[int] = {5, 10, 15, 30, 60}


class SensorReading(BaseModel):
    """Raw or calibrated reading from an IoT or gauge sensor station."""

    device_id: str = Field(..., min_length=1, description="Unique sensor identifier.")
    timestamp: datetime = Field(..., description="Timestamp of measurement.")
    latitude: float = Field(
        ...,
        ge=0.0,
        le=90.0,
        description="Northern hemisphere latitude in decimal degrees [0, 90].",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees [-180, 180].",
    )
    water_depth_m: float = Field(
        ...,
        ge=0.0,
        description="Inundation depth in metres above ground level.",
    )
    rainfall_mm: float = Field(
        ...,
        ge=0.0,
        description="Rainfall accumulation in millimetres for current timestep.",
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated sensor data reliability score in [0.0, 1.0].",
    )


class SensorQualityFlags(BaseModel):
    """Multi-factor sensor quality decomposition flags."""

    missingness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of missing readings in window [0.0, 1.0].",
    )
    stale: bool = Field(
        ...,
        description="Whether sensor readings have frozen/stuck unchanged.",
    )
    out_of_range: bool = Field(
        ...,
        description="Whether values exceed physical plausibility limits.",
    )
    spike: bool = Field(
        ...,
        description="Whether unphysical rate-of-change jump is detected.",
    )
    connectivity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Telemetry uplink link health/success ratio [0.0, 1.0].",
    )


class ObservationWindow(BaseModel):
    """Standardized spatio-temporal observation window aligned to an H3 cell."""

    h3_cell: str = Field(..., min_length=1, description="H3 index string of the cell.")
    start_time: datetime = Field(..., description="Start timestamp of the observation series.")
    timestep_minutes: int = Field(
        ...,
        description="Discrete timestep interval in minutes. Allowed: {5, 10, 15, 30, 60}.",
    )
    depth_series: List[float] = Field(
        ...,
        min_length=1,
        description="Sequential inundation depth measurements in metres.",
    )
    rainfall_series: List[float] = Field(
        ...,
        min_length=1,
        description="Sequential rainfall measurements in mm.",
    )
    quality_series: List[float] = Field(
        ...,
        min_length=1,
        description="Sequential sensor quality scores [0.0, 1.0].",
    )

    @field_validator("timestep_minutes")
    @classmethod
    def validate_timestep_minutes(cls, v: int) -> int:
        """Validate timestep against standard allowed intervals."""
        if v not in VALID_TIMESTEPS:
            raise ValueError(
                f"Invalid timestep_minutes {v}. Must be one of {sorted(VALID_TIMESTEPS)}."
            )
        return v

    @field_validator("depth_series")
    @classmethod
    def validate_depth_series(cls, v: List[float]) -> List[float]:
        """Verify non-negative depths."""
        for depth in v:
            if depth < 0.0:
                raise ValueError(f"Water depth cannot be negative, got {depth}")
        return v

    @field_validator("rainfall_series")
    @classmethod
    def validate_rainfall_series(cls, v: List[float]) -> List[float]:
        """Verify non-negative rainfall values."""
        for rain in v:
            if rain < 0.0:
                raise ValueError(f"Rainfall cannot be negative, got {rain}")
        return v

    @field_validator("quality_series")
    @classmethod
    def validate_quality_series(cls, v: List[float]) -> List[float]:
        """Verify quality scores fall in [0.0, 1.0]."""
        for q in v:
            if q < 0.0 or q > 1.0:
                raise ValueError(f"Quality score must be in [0.0, 1.0], got {q}")
        return v

    @model_validator(mode="after")
    def validate_equal_series_lengths(self) -> "ObservationWindow":
        """Ensure depth, rainfall, and quality series have identical lengths."""
        len_depth = len(self.depth_series)
        len_rain = len(self.rainfall_series)
        len_qual = len(self.quality_series)

        if not (len_depth == len_rain == len_qual):
            raise ValueError(
                f"All time series in ObservationWindow must have equal length: "
                f"depth={len_depth}, rainfall={len_rain}, quality={len_qual}."
            )
        return self
