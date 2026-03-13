"""Simulation configuration with Pydantic validation.

The Simulation dataclass encapsulates all parameters needed to define
an electromagnetic simulation: solver type, wavelength, materials,
geometry, boundary conditions, and solver-specific settings.

Validation happens locally before any API call is made, catching
configuration errors early.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class SolverType(str, Enum):
    """Supported electromagnetic solver types."""

    FDTD = "fdtd"
    RCWA = "rcwa"  # V2
    FEM = "fem"  # V3+


class BoundaryCondition(str, Enum):
    """Boundary condition types for the simulation domain."""

    PML = "pml"
    PERIODIC = "periodic"
    BLOCH = "bloch"
    SYMMETRIC = "symmetric"
    ANTISYMMETRIC = "antisymmetric"


class SourceType(str, Enum):
    """Electromagnetic source types."""

    PLANE_WAVE = "plane_wave"
    GAUSSIAN_BEAM = "gaussian_beam"
    MODE_SOURCE = "mode_source"
    DIPOLE = "dipole"


class PolarizationType(str, Enum):
    """Field polarization."""

    TE = "te"
    TM = "tm"


# ── Geometry primitives ──


class Box(BaseModel):
    """Rectangular box geometry."""

    type: Literal["box"] = "box"
    center: Tuple[float, float, float] = Field(..., description="Center (x, y, z) in meters")
    size: Tuple[float, float, float] = Field(..., description="Size (dx, dy, dz) in meters")
    material: str = Field(..., description="Material name from library or custom")

    @field_validator("size")
    @classmethod
    def size_must_be_positive(cls, v: Tuple[float, float, float]) -> Tuple[float, float, float]:
        if any(dim <= 0 for dim in v):
            raise ValueError("All dimensions must be positive")
        return v


class Cylinder(BaseModel):
    """Cylindrical geometry."""

    type: Literal["cylinder"] = "cylinder"
    center: Tuple[float, float, float]
    radius: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    axis: Literal["x", "y", "z"] = "z"
    material: str


class Sphere(BaseModel):
    """Spherical geometry."""

    type: Literal["sphere"] = "sphere"
    center: Tuple[float, float, float]
    radius: float = Field(..., gt=0)
    material: str


Geometry = Union[Box, Cylinder, Sphere]


# ── Source definition ──


class Source(BaseModel):
    """Electromagnetic source configuration."""

    source_type: SourceType = SourceType.PLANE_WAVE
    wavelength: Optional[float] = None
    frequency: Optional[float] = None
    polarization: PolarizationType = PolarizationType.TE
    direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    position: Optional[Tuple[float, float, float]] = None
    amplitude: float = Field(default=1.0, gt=0)

    @model_validator(mode="after")
    def check_wavelength_or_frequency(self) -> "Source":
        if self.wavelength is None and self.frequency is None:
            raise ValueError("Either wavelength or frequency must be specified")
        return self


# ── Monitor definition ──


class Monitor(BaseModel):
    """Field monitor for recording simulation data."""

    name: str = Field(..., min_length=1, max_length=64)
    monitor_type: Literal["field", "power", "mode"] = "field"
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    size: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    components: List[str] = Field(default=["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"])


# ── Simulation domain ──


class SimulationDomain(BaseModel):
    """Spatial domain and discretisation."""

    size: Tuple[float, float, float] = Field(
        ..., description="Domain size (x, y, z) in meters"
    )
    resolution: float = Field(
        default=20e-9,
        gt=0,
        description="Grid resolution in meters (default 20 nm)",
    )
    boundary_conditions: Tuple[
        BoundaryCondition, BoundaryCondition, BoundaryCondition
    ] = Field(
        default=(BoundaryCondition.PML, BoundaryCondition.PML, BoundaryCondition.PML),
        description="Boundary conditions for (x, y, z) axes",
    )
    pml_layers: int = Field(default=12, ge=4, le=64)


# ── Solver settings ──


class FDTDSettings(BaseModel):
    """FDTD-specific solver parameters."""

    time_steps: int = Field(default=20000, ge=100, le=1_000_000)
    courant_factor: float = Field(default=0.99, gt=0, le=1.0)
    convergence_threshold: float = Field(default=1e-6, gt=0)
    check_every_n: int = Field(default=1000, ge=100)


class RCWASettings(BaseModel):
    """RCWA-specific solver parameters (V2)."""

    num_harmonics: int = Field(default=11, ge=1, le=101)
    wavelength_start: float = Field(..., gt=0)
    wavelength_end: float = Field(..., gt=0)
    num_wavelengths: int = Field(default=100, ge=1)


# ── Main simulation config ──


class SimulationConfig(BaseModel):
    """Complete simulation configuration.

    This is the Pydantic model that gets serialised to JSON and sent
    to the API. All validation happens here before submission.
    """

    solver: SolverType = SolverType.FDTD
    domain: SimulationDomain
    source: Source
    structures: List[Geometry] = Field(default_factory=list, min_length=1)
    monitors: List[Monitor] = Field(default_factory=list)
    fdtd_settings: Optional[FDTDSettings] = None
    rcwa_settings: Optional[RCWASettings] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def solver_settings_match(self) -> "SimulationConfig":
        if self.solver == SolverType.FDTD and self.fdtd_settings is None:
            self.fdtd_settings = FDTDSettings()
        if self.solver == SolverType.RCWA and self.rcwa_settings is None:
            raise ValueError("RCWA solver requires rcwa_settings")
        return self

    def to_json(self) -> str:
        """Serialise config to JSON string for API submission."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "SimulationConfig":
        """Deserialise config from JSON string."""
        return cls.model_validate_json(json_str)


class Simulation:
    """High-level simulation wrapper for user convenience.

    Provides a simpler constructor than the full SimulationConfig
    Pydantic model, while still performing validation.

    Args:
        solver: Solver type ('fdtd', 'rcwa', 'fem').
        wavelength: Operating wavelength in meters.
        materials: List of material names used in the simulation.
        geometry: List of geometry primitives or a single structure.
        domain_size: Simulation domain size (x, y, z) in meters.
        resolution: Grid resolution in meters.
        time_steps: Number of FDTD time steps.
        monitors: List of Monitor configurations.
        metadata: Arbitrary metadata dict stored with results.

    Example:
        >>> sim = Simulation(
        ...     solver="fdtd",
        ...     wavelength=1.55e-6,
        ...     materials=["Si", "SiO2"],
        ...     geometry=[Box(center=(0,0,0), size=(1e-6, 1e-6, 0.22e-6), material="Si")],
        ...     domain_size=(4e-6, 4e-6, 4e-6),
        ... )
    """

    def __init__(
        self,
        solver: str = "fdtd",
        wavelength: float = 1.55e-6,
        materials: Optional[List[str]] = None,
        geometry: Optional[Union[List[Geometry], Geometry]] = None,
        domain_size: Tuple[float, float, float] = (4e-6, 4e-6, 4e-6),
        resolution: float = 20e-9,
        time_steps: int = 20000,
        monitors: Optional[List[Monitor]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Normalise geometry to list
        structures: List[Geometry]
        if geometry is None:
            structures = [
                Box(center=(0, 0, 0), size=(1e-6, 1e-6, 0.22e-6), material="Si")
            ]
        elif isinstance(geometry, list):
            structures = geometry
        else:
            structures = [geometry]

        self.config = SimulationConfig(
            solver=SolverType(solver),
            domain=SimulationDomain(size=domain_size, resolution=resolution),
            source=Source(wavelength=wavelength),
            structures=structures,
            monitors=monitors or [],
            fdtd_settings=FDTDSettings(time_steps=time_steps)
            if solver == "fdtd"
            else None,
            metadata=metadata or {},
        )

    def to_json(self) -> str:
        """Serialise to JSON."""
        return self.config.to_json()

    def __repr__(self) -> str:
        return (
            f"Simulation(solver={self.config.solver.value!r}, "
            f"structures={len(self.config.structures)}, "
            f"monitors={len(self.config.monitors)})"
        )
