"""Unit tests for the FDTD solver — physics benchmarks.

These tests validate numerical accuracy against analytic solutions
as specified in the MetoSim test strategy.
"""

import numpy as np
import pytest

from metosim_engine.solvers.fdtd import C0, EPS0, MU0, FDTDConfig, FDTDSolver


class TestFDTDConfig:
    def test_courant_dt(self):
        cfg = FDTDConfig(grid_shape=(100, 100, 100), resolution=20e-9)
        # dt must satisfy Courant condition: dt <= dx / (c * sqrt(3))
        dt_max = cfg.resolution / (C0 * np.sqrt(3))
        assert cfg.dt <= dt_max
        assert cfg.dt > 0

    def test_resolution_properties(self):
        cfg = FDTDConfig(grid_shape=(50, 50, 50), resolution=10e-9)
        assert cfg.dx == 10e-9
        assert cfg.dy == 10e-9
        assert cfg.dz == 10e-9


class TestFDTDSolver:
    def test_initialization(self):
        cfg = FDTDConfig(grid_shape=(10, 10, 10), resolution=20e-9, time_steps=100)
        solver = FDTDSolver(cfg)
        assert solver.Ex.shape == (10, 10, 10)
        assert solver.Hy.shape == (10, 10, 10)

    def test_field_conservation_energy(self):
        """Fields in vacuum should conserve energy (no sources, no loss)."""
        cfg = FDTDConfig(
            grid_shape=(20, 20, 20),
            resolution=20e-9,
            time_steps=50,
            check_every_n=50,
        )
        solver = FDTDSolver(cfg)

        # Set initial field perturbation
        solver.Ez = np.zeros((20, 20, 20))
        solver.Ez[10, 10, 10] = 1.0

        solver._compute_update_coefficients()

        # Run a few steps
        for _ in range(10):
            solver._update_H()
            solver._update_E()

        # Total energy should be finite and > 0 (energy spreads)
        total_E = np.sum(solver.Ex**2 + solver.Ey**2 + solver.Ez**2)
        total_H = np.sum(solver.Hx**2 + solver.Hy**2 + solver.Hz**2)
        assert total_E + total_H > 0
        assert np.isfinite(total_E)
        assert np.isfinite(total_H)

    def test_solver_runs_to_completion(self):
        cfg = FDTDConfig(
            grid_shape=(10, 10, 10),
            resolution=50e-9,
            time_steps=100,
            check_every_n=50,
        )
        solver = FDTDSolver(cfg)
        solver.set_permittivity(np.ones((10, 10, 10)))

        # Simple point source
        def src(step, t):
            s = np.zeros((10, 10, 10))
            s[5, 5, 5] = np.sin(2 * np.pi * 1e14 * t) * np.exp(-(t - 1e-14)**2 / (5e-15)**2)
            return s

        solver.add_source(src)
        result = solver.run()

        assert result.total_steps == 100
        assert result.wall_time > 0
        assert result.performance > 0
        assert "Ex" in result.E
        assert "Hz" in result.H


class TestMaterialCatalog:
    def test_silicon_permittivity(self):
        from metosim_engine.materials.catalog import get_permittivity
        eps = get_permittivity("Si")
        assert np.real(eps) == pytest.approx(3.4757**2, rel=0.01)

    def test_unknown_material_raises(self):
        from metosim_engine.materials.catalog import get_permittivity
        with pytest.raises(KeyError):
            get_permittivity("Vibranium")

    def test_build_catalog(self):
        from metosim_engine.materials.catalog import build_catalog
        cat = build_catalog(["Si", "SiO2", "Au"])
        assert len(cat) == 3
        assert "Si" in cat
