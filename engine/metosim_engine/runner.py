"""Engine runner — entry point for simulation execution.

Receives a simulation job, dispatches to the appropriate solver,
manages mesh generation, and writes results to HDF5.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from metosim_engine.io.hdf5_writer import write_results
from metosim_engine.materials.catalog import build_catalog, get_permittivity
from metosim_engine.mesh.mesher import generate_mesh
from metosim_engine.solvers.fdtd import FDTDConfig, FDTDSolver

logger = logging.getLogger("metosim.engine.runner")


def run_simulation(
    config: Dict[str, Any],
    output_dir: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Execute a simulation from a configuration dict.

    This is the main entry point called by Celery/Modal workers.

    Args:
        config: Full simulation configuration (from API).
        output_dir: Directory for result HDF5. Uses temp dir if None.

    Returns:
        Dict with 'result_path', 'checksum', 'wall_time', 'converged'.
    """
    solver_type = config.get("solver", "fdtd")

    if solver_type != "fdtd":
        raise NotImplementedError(f"Solver '{solver_type}' not available in V1")

    logger.info(f"Starting {solver_type.upper()} simulation")

    # ── Extract config ──
    domain = config["domain"]
    source_cfg = config["source"]
    structures = config["structures"]
    fdtd_cfg = config.get("fdtd_settings", {})
    metadata = config.get("metadata", {})

    resolution = domain.get("resolution", 20e-9)
    domain_size = tuple(domain["size"])

    # Compute grid shape from domain size and resolution
    grid_shape = tuple(max(1, int(s / resolution)) for s in domain_size)
    logger.info(f"Grid: {grid_shape[0]}×{grid_shape[1]}×{grid_shape[2]}")

    # ── Build material catalog ──
    material_names = list(set(s["material"] for s in structures))
    wavelength = source_cfg.get("wavelength", 1.55e-6)
    catalog = build_catalog(material_names, wavelength)

    # ── Generate mesh ──
    eps_grid = generate_mesh(
        grid_shape=grid_shape,
        resolution=resolution,
        structures=structures,
        material_catalog=catalog,
    )

    # ── Configure solver ──
    solver = FDTDSolver(
        FDTDConfig(
            grid_shape=grid_shape,
            resolution=resolution,
            time_steps=fdtd_cfg.get("time_steps", 20000),
            courant_factor=fdtd_cfg.get("courant_factor", 0.99),
            convergence_threshold=fdtd_cfg.get("convergence_threshold", 1e-6),
            check_every_n=fdtd_cfg.get("check_every_n", 1000),
        )
    )

    solver.set_permittivity(np.real(eps_grid))

    # ── Add source ──
    # Simple Gaussian pulse source for MVP
    freq = 2 * np.pi * 3e8 / wavelength
    sigma_t = 3.0 / freq

    def source_fn(step: int, t: float) -> np.ndarray:
        src = np.zeros(grid_shape)
        # Point source at domain center
        cx, cy, cz = [s // 2 for s in grid_shape]
        amplitude = np.exp(-((t - 3 * sigma_t) ** 2) / (2 * sigma_t**2))
        amplitude *= np.sin(freq * t)
        src[cx, cy, cz] = amplitude
        return src

    solver.add_source(source_fn)

    # ── Run ──
    result = solver.run()

    # ── Write HDF5 ──
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="metosim_")
    output_path = Path(output_dir) / "results.hdf5"

    checksum = write_results(
        filepath=output_path,
        E_fields=result.E,
        H_fields=result.H,
        config=config,
        permittivity=eps_grid,
        convergence=result.convergence,
        metadata={
            **metadata,
            "wall_time": result.wall_time,
            "total_steps": result.total_steps,
            "converged": result.converged,
            "performance": result.performance,
        },
    )

    logger.info(
        f"Simulation complete: {result.wall_time:.2f}s, "
        f"converged={result.converged}, checksum={checksum[:12]}..."
    )

    return {
        "result_path": str(output_path),
        "checksum": checksum,
        "wall_time": result.wall_time,
        "converged": result.converged,
        "total_steps": result.total_steps,
        "performance": result.performance,
    }
