"""Material permittivity database for the simulation engine.

Server-side counterpart to the SDK's material library. Provides
wavelength-dependent complex permittivity for mesh generation.
"""

from __future__ import annotations

from typing import Dict

import numpy as np

# Telecom C-band (1550 nm) default permittivities
CATALOG_1550NM: Dict[str, complex] = {
    "Si": complex(3.4757**2, 0),
    "SiO2": complex(1.4440**2, 0),
    "TiO2": complex(2.27**2, 0),
    "Si3N4": complex(1.994**2, 0),
    "Air": complex(1.0, 0),
}

# Metals (Drude model at 1550 nm)
_omega_1550 = 2 * np.pi * 3e8 / 1.55e-6

_au_eps = 1.0 - (1.37e16)**2 / (_omega_1550**2 + 1j * 4.05e13 * _omega_1550)
CATALOG_1550NM["Au"] = complex(_au_eps)

_al_eps = 1.0 - (2.24e16)**2 / (_omega_1550**2 + 1j * 1.22e14 * _omega_1550)
CATALOG_1550NM["Al"] = complex(_al_eps)


def get_permittivity(material: str, wavelength: float = 1.55e-6) -> complex:
    """Look up material permittivity.

    Args:
        material: Material name/formula.
        wavelength: Wavelength in meters (default 1550 nm).

    Returns:
        Complex relative permittivity.

    Raises:
        KeyError: If material not found.
    """
    key = material.strip()
    # Try exact match first, then case-insensitive
    if key in CATALOG_1550NM:
        return CATALOG_1550NM[key]

    for k, v in CATALOG_1550NM.items():
        if k.lower() == key.lower():
            return v

    available = ", ".join(sorted(CATALOG_1550NM.keys()))
    raise KeyError(f"Material '{material}' not found. Available: {available}")


def build_catalog(
    material_names: list[str],
    wavelength: float = 1.55e-6,
) -> Dict[str, complex]:
    """Build a permittivity catalog for a set of materials.

    Args:
        material_names: List of material names.
        wavelength: Operating wavelength.

    Returns:
        Dict mapping material name → complex permittivity.
    """
    return {name: get_permittivity(name, wavelength) for name in material_names}
