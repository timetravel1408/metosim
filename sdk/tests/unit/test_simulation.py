"""Unit tests for simulation configuration and validation."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from metosim.simulation import (
    Box,
    BoundaryCondition,
    Cylinder,
    FDTDSettings,
    Monitor,
    Simulation,
    SimulationConfig,
    SimulationDomain,
    SolverType,
    Source,
    Sphere,
)


class TestSimulationConfig:
    """Tests for SimulationConfig Pydantic model."""

    def test_valid_config_creates_simulation(self):
        config = SimulationConfig(
            solver=SolverType.FDTD,
            domain=SimulationDomain(size=(4e-6, 4e-6, 4e-6)),
            source=Source(wavelength=1.55e-6),
            structures=[Box(center=(0, 0, 0), size=(1e-6, 1e-6, 0.22e-6), material="Si")],
        )
        assert config.solver == SolverType.FDTD
        assert config.fdtd_settings is not None
        assert config.fdtd_settings.time_steps == 20000

    def test_invalid_wavelength_raises(self):
        with pytest.raises(PydanticValidationError):
            Source(wavelength=None, frequency=None)

    def test_missing_structures_raises(self):
        with pytest.raises(PydanticValidationError):
            SimulationConfig(
                solver=SolverType.FDTD,
                domain=SimulationDomain(size=(4e-6, 4e-6, 4e-6)),
                source=Source(wavelength=1.55e-6),
                structures=[],  # min_length=1
            )

    def test_negative_box_size_raises(self):
        with pytest.raises(PydanticValidationError):
            Box(center=(0, 0, 0), size=(-1e-6, 1e-6, 1e-6), material="Si")

    def test_fdtd_settings_auto_created(self):
        config = SimulationConfig(
            solver=SolverType.FDTD,
            domain=SimulationDomain(size=(1e-6, 1e-6, 1e-6)),
            source=Source(wavelength=1.55e-6),
            structures=[Box(center=(0, 0, 0), size=(0.5e-6, 0.5e-6, 0.2e-6), material="Si")],
        )
        assert config.fdtd_settings is not None

    def test_rcwa_without_settings_raises(self):
        with pytest.raises(PydanticValidationError):
            SimulationConfig(
                solver=SolverType.RCWA,
                domain=SimulationDomain(size=(1e-6, 1e-6, 1e-6)),
                source=Source(wavelength=1.55e-6),
                structures=[Box(center=(0, 0, 0), size=(0.5e-6, 0.5e-6, 0.2e-6), material="Si")],
            )

    def test_json_serialization_roundtrip(self):
        config = SimulationConfig(
            solver=SolverType.FDTD,
            domain=SimulationDomain(size=(2e-6, 2e-6, 2e-6), resolution=10e-9),
            source=Source(wavelength=1.55e-6),
            structures=[
                Box(center=(0, 0, 0), size=(1e-6, 1e-6, 0.22e-6), material="Si"),
                Sphere(center=(0, 0, 0.5e-6), radius=0.1e-6, material="TiO2"),
            ],
            monitors=[Monitor(name="center", center=(0, 0, 0))],
        )
        json_str = config.to_json()
        restored = SimulationConfig.from_json(json_str)
        assert restored.solver == config.solver
        assert len(restored.structures) == 2
        assert len(restored.monitors) == 1


class TestSimulationWrapper:
    """Tests for the high-level Simulation convenience class."""

    def test_default_creates_valid_sim(self):
        sim = Simulation()
        assert sim.config.solver == SolverType.FDTD
        assert len(sim.config.structures) == 1

    def test_custom_params(self):
        sim = Simulation(
            solver="fdtd",
            wavelength=1.31e-6,
            geometry=[
                Box(center=(0, 0, 0), size=(1e-6, 1e-6, 0.22e-6), material="Si"),
            ],
            domain_size=(8e-6, 8e-6, 4e-6),
            resolution=10e-9,
            time_steps=50000,
        )
        assert sim.config.source.wavelength == 1.31e-6
        assert sim.config.domain.resolution == 10e-9
        assert sim.config.fdtd_settings.time_steps == 50000

    def test_repr(self):
        sim = Simulation()
        r = repr(sim)
        assert "Simulation" in r
        assert "fdtd" in r


class TestGeometryPrimitives:
    """Tests for Box, Cylinder, Sphere validation."""

    def test_valid_box(self):
        b = Box(center=(0, 0, 0), size=(1, 1, 1), material="Si")
        assert b.type == "box"

    def test_valid_cylinder(self):
        c = Cylinder(center=(0, 0, 0), radius=0.5, height=1.0, material="Si")
        assert c.type == "cylinder"

    def test_valid_sphere(self):
        s = Sphere(center=(0, 0, 0), radius=0.5, material="Au")
        assert s.type == "sphere"

    def test_negative_radius_raises(self):
        with pytest.raises(PydanticValidationError):
            Sphere(center=(0, 0, 0), radius=-1, material="Si")
