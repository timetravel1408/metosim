"""Mesh generation for FDTD simulations.

Converts geometric primitives (boxes, cylinders, spheres) into
discretised permittivity grids on the Yee lattice.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import numpy as np

logger = logging.getLogger("metosim.engine.mesh")


def generate_mesh(
    grid_shape: Tuple[int, int, int],
    resolution: float,
    structures: List[Dict[str, Any]],
    material_catalog: Dict[str, complex],
    background_eps: float = 1.0,
) -> np.ndarray:
    """Generate a 3D permittivity grid from geometric primitives.

    Args:
        grid_shape: (Nx, Ny, Nz) grid dimensions.
        resolution: Grid cell size in meters.
        structures: List of geometry dicts with 'type', 'center',
                    'size'/'radius', and 'material' keys.
        material_catalog: Mapping of material name → permittivity.
        background_eps: Background relative permittivity.

    Returns:
        3D complex ndarray of relative permittivity.
    """
    Nx, Ny, Nz = grid_shape
    eps_grid = np.full((Nx, Ny, Nz), background_eps, dtype=np.complex128)

    # Coordinate arrays (cell centers)
    x = (np.arange(Nx) + 0.5) * resolution
    y = (np.arange(Ny) + 0.5) * resolution
    z = (np.arange(Nz) + 0.5) * resolution
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

    for struct in structures:
        geo_type = struct.get("type", "box")
        material_name = struct["material"]
        eps_val = material_catalog.get(material_name, background_eps)

        if geo_type == "box":
            cx, cy, cz = struct["center"]
            sx, sy, sz = struct["size"]
            mask = (
                (np.abs(X - cx) <= sx / 2)
                & (np.abs(Y - cy) <= sy / 2)
                & (np.abs(Z - cz) <= sz / 2)
            )
        elif geo_type == "cylinder":
            cx, cy, cz = struct["center"]
            radius = struct["radius"]
            height = struct["height"]
            axis = struct.get("axis", "z")
            if axis == "z":
                mask = ((X - cx) ** 2 + (Y - cy) ** 2 <= radius ** 2) & (
                    np.abs(Z - cz) <= height / 2
                )
            elif axis == "y":
                mask = ((X - cx) ** 2 + (Z - cz) ** 2 <= radius ** 2) & (
                    np.abs(Y - cy) <= height / 2
                )
            else:
                mask = ((Y - cy) ** 2 + (Z - cz) ** 2 <= radius ** 2) & (
                    np.abs(X - cx) <= height / 2
                )
        elif geo_type == "sphere":
            cx, cy, cz = struct["center"]
            radius = struct["radius"]
            mask = (X - cx) ** 2 + (Y - cy) ** 2 + (Z - cz) ** 2 <= radius ** 2
        else:
            logger.warning(f"Unknown geometry type: {geo_type}, skipping")
            continue

        eps_grid[mask] = eps_val
        logger.debug(
            f"Placed {geo_type} ({material_name}): "
            f"{np.sum(mask)} cells, eps={eps_val}"
        )

    logger.info(
        f"Mesh generated: {Nx}×{Ny}×{Nz}, "
        f"{len(structures)} structures, "
        f"eps range [{np.real(eps_grid).min():.2f}, {np.real(eps_grid).max():.2f}]"
    )

    return eps_grid
