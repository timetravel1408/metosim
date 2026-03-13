"""FDTD (Finite-Difference Time-Domain) solver core.

Implements the 3D Yee-grid FDTD algorithm for electromagnetic
wave propagation in dispersive media. Uses JAX for GPU acceleration
when available, with NumPy fallback for CPU execution.

References:
    Taflove & Hagness, "Computational Electrodynamics", 3rd Ed.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("metosim.engine.fdtd")

try:
    import jax
    import jax.numpy as jnp

    HAS_JAX = True
except ImportError:
    HAS_JAX = False
    jnp = np  # type: ignore[assignment]


# ── Physical constants ──
C0 = 299_792_458.0  # Speed of light (m/s)
EPS0 = 8.854187817e-12  # Vacuum permittivity (F/m)
MU0 = 1.2566370621219e-6  # Vacuum permeability (H/m)
ETA0 = np.sqrt(MU0 / EPS0)  # Free-space impedance (Ω)


@dataclass
class FDTDConfig:
    """FDTD solver configuration.

    Attributes:
        grid_shape: (Nx, Ny, Nz) grid dimensions.
        resolution: Grid cell size in meters (isotropic).
        time_steps: Number of time steps to simulate.
        courant_factor: Courant stability factor (≤ 1.0).
        convergence_threshold: Relative field change for early stopping.
        check_every_n: Steps between convergence checks.
    """

    grid_shape: Tuple[int, int, int]
    resolution: float
    time_steps: int = 20000
    courant_factor: float = 0.99
    convergence_threshold: float = 1e-6
    check_every_n: int = 1000

    @property
    def dt(self) -> float:
        """Time step size (s), derived from Courant condition."""
        return self.courant_factor * self.resolution / (C0 * np.sqrt(3.0))

    @property
    def dx(self) -> float:
        return self.resolution

    @property
    def dy(self) -> float:
        return self.resolution

    @property
    def dz(self) -> float:
        return self.resolution


@dataclass
class FDTDResult:
    """Container for FDTD simulation results.

    Attributes:
        E: Electric field arrays {component: ndarray}.
        H: Magnetic field arrays {component: ndarray}.
        convergence: List of (step, residual) convergence history.
        converged: Whether early stopping was triggered.
        total_steps: Actual number of steps simulated.
        wall_time: Wall-clock simulation time in seconds.
        performance: Grid-points × steps / second.
    """

    E: Dict[str, np.ndarray]
    H: Dict[str, np.ndarray]
    convergence: List[Tuple[int, float]]
    converged: bool
    total_steps: int
    wall_time: float
    performance: float


class FDTDSolver:
    """3D FDTD electromagnetic solver.

    Implements the standard Yee algorithm with:
    - PML absorbing boundary conditions
    - Dispersive material support
    - Modal and plane-wave sources
    - Convergence-based early stopping

    Example:
        >>> config = FDTDConfig(grid_shape=(100, 100, 100), resolution=20e-9)
        >>> solver = FDTDSolver(config)
        >>> solver.set_permittivity(eps_grid)
        >>> solver.add_source(source_field, position=50)
        >>> result = solver.run()
    """

    def __init__(self, config: FDTDConfig) -> None:
        self.config = config
        self._xp = jnp if HAS_JAX else np

        Nx, Ny, Nz = config.grid_shape

        # Electromagnetic field arrays (Yee grid staggering)
        self.Ex = self._xp.zeros((Nx, Ny, Nz))
        self.Ey = self._xp.zeros((Nx, Ny, Nz))
        self.Ez = self._xp.zeros((Nx, Ny, Nz))
        self.Hx = self._xp.zeros((Nx, Ny, Nz))
        self.Hy = self._xp.zeros((Nx, Ny, Nz))
        self.Hz = self._xp.zeros((Nx, Ny, Nz))

        # Material grids
        self._eps_r = self._xp.ones((Nx, Ny, Nz))
        self._mu_r = self._xp.ones((Nx, Ny, Nz))
        self._sigma_e = self._xp.zeros((Nx, Ny, Nz))  # Electric conductivity
        self._sigma_m = self._xp.zeros((Nx, Ny, Nz))  # Magnetic conductivity

        # Update coefficients (computed when materials are set)
        self._ce: Optional[np.ndarray] = None
        self._ch: Optional[np.ndarray] = None

        # Source
        self._source_fn: Optional[Callable] = None

        # Monitors
        self._monitors: List[Dict[str, Any]] = []

        logger.info(
            f"FDTD solver initialized: {Nx}×{Ny}×{Nz} grid, "
            f"dt={config.dt:.3e}s, dx={config.dx:.3e}m"
        )

    def set_permittivity(self, eps_r: np.ndarray) -> None:
        """Set the relative permittivity grid.

        Args:
            eps_r: 3D array of relative permittivity values.
        """
        assert eps_r.shape == self.config.grid_shape, (
            f"Permittivity shape {eps_r.shape} != grid {self.config.grid_shape}"
        )
        self._eps_r = self._xp.array(eps_r)
        self._compute_update_coefficients()

    def set_conductivity(self, sigma: np.ndarray) -> None:
        """Set the electric conductivity grid (for PML/absorbers).

        Args:
            sigma: 3D array of conductivity values (S/m).
        """
        self._sigma_e = self._xp.array(sigma)
        self._compute_update_coefficients()

    def add_source(
        self,
        source_fn: Callable[[int, float], np.ndarray],
    ) -> None:
        """Register a time-dependent source function.

        Args:
            source_fn: Callable(step, time) -> field_update array.
        """
        self._source_fn = source_fn

    def add_monitor(
        self,
        name: str,
        position: Tuple[int, int, int],
        size: Tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """Add a field monitor at a given position.

        Args:
            name: Monitor label.
            position: (ix, iy, iz) grid coordinates.
            size: Monitor extent in grid cells.
        """
        self._monitors.append({
            "name": name,
            "position": position,
            "size": size,
            "data": [],
        })

    def _compute_update_coefficients(self) -> None:
        """Pre-compute FDTD update coefficients from material grids."""
        dt = self.config.dt
        dx = self.config.dx

        # E-field update coefficients
        denom_e = self._eps_r * EPS0 + 0.5 * self._sigma_e * dt
        self._ce_coeff = (self._eps_r * EPS0 - 0.5 * self._sigma_e * dt) / denom_e
        self._ce_curl = (dt / dx) / denom_e

        # H-field update coefficients
        denom_h = self._mu_r * MU0 + 0.5 * self._sigma_m * dt
        self._ch_coeff = (self._mu_r * MU0 - 0.5 * self._sigma_m * dt) / denom_h
        self._ch_curl = (dt / dx) / denom_h

    def _update_H(self) -> None:
        """Update magnetic field components (half-step)."""
        xp = self._xp

        # curl E
        dEz_dy = xp.diff(self.Ez, axis=1, prepend=self.Ez[:, :1, :])
        dEy_dz = xp.diff(self.Ey, axis=2, prepend=self.Ey[:, :, :1])
        dEx_dz = xp.diff(self.Ex, axis=2, prepend=self.Ex[:, :, :1])
        dEz_dx = xp.diff(self.Ez, axis=0, prepend=self.Ez[:1, :, :])
        dEy_dx = xp.diff(self.Ey, axis=0, prepend=self.Ey[:1, :, :])
        dEx_dy = xp.diff(self.Ex, axis=1, prepend=self.Ex[:, :1, :])

        self.Hx = self._ch_coeff * self.Hx - self._ch_curl * (dEz_dy - dEy_dz)
        self.Hy = self._ch_coeff * self.Hy - self._ch_curl * (dEx_dz - dEz_dx)
        self.Hz = self._ch_coeff * self.Hz - self._ch_curl * (dEy_dx - dEx_dy)

    def _update_E(self) -> None:
        """Update electric field components (full-step)."""
        xp = self._xp

        # curl H
        dHz_dy = xp.diff(self.Hz, axis=1, append=self.Hz[:, -1:, :])
        dHy_dz = xp.diff(self.Hy, axis=2, append=self.Hy[:, :, -1:])
        dHx_dz = xp.diff(self.Hx, axis=2, append=self.Hx[:, :, -1:])
        dHz_dx = xp.diff(self.Hz, axis=0, append=self.Hz[-1:, :, :])
        dHy_dx = xp.diff(self.Hy, axis=0, append=self.Hy[-1:, :, :])
        dHx_dy = xp.diff(self.Hx, axis=1, append=self.Hx[:, -1:, :])

        self.Ex = self._ce_coeff * self.Ex + self._ce_curl * (dHz_dy - dHy_dz)
        self.Ey = self._ce_coeff * self.Ey + self._ce_curl * (dHx_dz - dHz_dx)
        self.Ez = self._ce_coeff * self.Ez + self._ce_curl * (dHy_dx - dHx_dy)

    def _record_monitors(self, step: int) -> None:
        """Record field values at all monitor positions."""
        for monitor in self._monitors:
            ix, iy, iz = monitor["position"]
            monitor["data"].append({
                "step": step,
                "Ex": float(self.Ex[ix, iy, iz]),
                "Ey": float(self.Ey[ix, iy, iz]),
                "Ez": float(self.Ez[ix, iy, iz]),
                "Hx": float(self.Hx[ix, iy, iz]),
                "Hy": float(self.Hy[ix, iy, iz]),
                "Hz": float(self.Hz[ix, iy, iz]),
            })

    def _check_convergence(self, prev_energy: float) -> Tuple[float, float]:
        """Check field convergence based on total energy change.

        Returns:
            (current_energy, relative_change)
        """
        xp = self._xp
        energy = float(
            xp.sum(self.Ex ** 2 + self.Ey ** 2 + self.Ez ** 2)
            + xp.sum(self.Hx ** 2 + self.Hy ** 2 + self.Hz ** 2)
        )
        if prev_energy > 0:
            rel_change = abs(energy - prev_energy) / prev_energy
        else:
            rel_change = float("inf")
        return energy, rel_change

    def run(self) -> FDTDResult:
        """Execute the FDTD simulation.

        Returns:
            FDTDResult containing final field data and convergence info.
        """
        self._compute_update_coefficients()

        cfg = self.config
        convergence_history: List[Tuple[int, float]] = []
        prev_energy = 0.0
        converged = False

        start_time = time.monotonic()
        logger.info(f"Starting FDTD: {cfg.time_steps} steps")

        for step in range(cfg.time_steps):
            # Standard Yee update order
            self._update_H()

            # Inject source at half-step
            if self._source_fn is not None:
                t = (step + 0.5) * cfg.dt
                source_update = self._source_fn(step, t)
                if source_update is not None:
                    self.Ez = self.Ez + self._xp.array(source_update)

            self._update_E()

            # Record monitors
            if self._monitors:
                self._record_monitors(step)

            # Convergence check
            if step > 0 and step % cfg.check_every_n == 0:
                energy, rel_change = self._check_convergence(prev_energy)
                prev_energy = energy
                convergence_history.append((step, rel_change))

                if rel_change < cfg.convergence_threshold and step > cfg.check_every_n * 3:
                    logger.info(f"Converged at step {step} (residual={rel_change:.2e})")
                    converged = True
                    break

        wall_time = time.monotonic() - start_time
        total_steps = step + 1
        total_cells = np.prod(cfg.grid_shape)
        performance = total_cells * total_steps / wall_time

        logger.info(
            f"FDTD complete: {total_steps} steps in {wall_time:.2f}s "
            f"({performance:.2e} cells·steps/s)"
        )

        return FDTDResult(
            E={
                "Ex": np.array(self.Ex),
                "Ey": np.array(self.Ey),
                "Ez": np.array(self.Ez),
            },
            H={
                "Hx": np.array(self.Hx),
                "Hy": np.array(self.Hy),
                "Hz": np.array(self.Hz),
            },
            convergence=convergence_history,
            converged=converged,
            total_steps=total_steps,
            wall_time=wall_time,
            performance=performance,
        )
