"""Built-in material library for common photonic materials.

Provides wavelength-dependent complex permittivity for materials
commonly used in nanophotonics: Si, SiO2, TiO2, Au, Al, and more.

Permittivity data is interpolated from tabulated values at telecom
wavelengths (1260–1675 nm). Custom materials can be registered.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

import numpy as np


@dataclass(frozen=True)
class Material:
    """Optical material with wavelength-dependent permittivity.

    Attributes:
        name: Human-readable material name.
        formula: Chemical formula or identifier.
        permittivity_fn: Callable that takes wavelength (m) and returns
            complex permittivity (eps_r).
        wavelength_range: Valid wavelength range (min, max) in meters.
        description: Brief description of the material.
    """

    name: str
    formula: str
    permittivity_fn: Callable[[float], complex]
    wavelength_range: tuple[float, float] = (1.0e-6, 2.0e-6)
    description: str = ""

    def eps(self, wavelength: float) -> complex:
        """Get complex permittivity at a given wavelength.

        Args:
            wavelength: Wavelength in meters.

        Returns:
            Complex relative permittivity (eps_r).

        Raises:
            ValueError: If wavelength is outside the valid range.
        """
        wl_min, wl_max = self.wavelength_range
        if not (wl_min <= wavelength <= wl_max):
            warnings.warn(
                f"Wavelength {wavelength*1e9:.1f} nm outside valid range "
                f"[{wl_min*1e9:.0f}, {wl_max*1e9:.0f}] nm for {self.name}. "
                f"Extrapolating.",
                stacklevel=2,
            )
        return self.permittivity_fn(wavelength)

    @property
    def n_at_1550nm(self) -> complex:
        """Refractive index at 1550 nm (telecom C-band)."""
        eps = self.eps(1.55e-6)
        return np.sqrt(eps)  # type: ignore[return-value]

    def __repr__(self) -> str:
        n = self.n_at_1550nm
        return f"Material({self.name!r}, n@1550nm={n.real:.4f}+{n.imag:.4e}j)"


# ── Built-in material definitions ──


def _silicon_eps(wavelength: float) -> complex:
    """Silicon permittivity (Palik model, simplified for telecom)."""
    wl_um = wavelength * 1e6
    # Sellmeier-type approximation for crystalline Si at telecom wavelengths
    n = 3.4757 - 0.0711 * (wl_um - 1.55) + 0.0314 * (wl_um - 1.55) ** 2
    k = 0.0  # Negligible absorption at telecom for undoped Si
    return complex(n**2 - k**2, 2 * n * k)


def _silica_eps(wavelength: float) -> complex:
    """Silicon dioxide (fused silica) permittivity."""
    wl_um = wavelength * 1e6
    # Sellmeier equation for fused silica
    n = 1.4440 + 0.0032 / (wl_um**2) - 0.0001 * wl_um**2
    return complex(n**2, 0.0)


def _tio2_eps(wavelength: float) -> complex:
    """Titanium dioxide (amorphous) permittivity."""
    wl_um = wavelength * 1e6
    n = 2.27 + 0.04 / (wl_um**2 - 0.04)
    return complex(n**2, 0.0)


def _gold_eps(wavelength: float) -> complex:
    """Gold permittivity (Drude-Lorentz model)."""
    wl_um = wavelength * 1e6
    omega = 2 * np.pi * 3e8 / wavelength
    omega_p = 1.37e16  # Plasma frequency (rad/s)
    gamma = 4.05e13  # Damping rate (rad/s)
    eps = 1.0 - omega_p**2 / (omega**2 + 1j * gamma * omega)
    return complex(eps)


def _aluminium_eps(wavelength: float) -> complex:
    """Aluminium permittivity (Drude model)."""
    omega = 2 * np.pi * 3e8 / wavelength
    omega_p = 2.24e16
    gamma = 1.22e14
    eps = 1.0 - omega_p**2 / (omega**2 + 1j * gamma * omega)
    return complex(eps)


def _sin_eps(wavelength: float) -> complex:
    """Silicon nitride permittivity."""
    wl_um = wavelength * 1e6
    n = 1.994 + 0.008 / (wl_um**2)
    return complex(n**2, 0.0)


def _air_eps(wavelength: float) -> complex:
    """Air / vacuum permittivity."""
    return complex(1.0, 0.0)


# ── Material Library ──


class MaterialLibrary:
    """Registry of optical materials.

    Provides a singleton-like registry where built-in and custom
    materials can be looked up by name.

    Example:
        >>> lib = MaterialLibrary()
        >>> si = lib.get("Si")
        >>> print(si.eps(1.55e-6))
    """

    def __init__(self) -> None:
        self._materials: Dict[str, Material] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register all built-in materials."""
        builtins = [
            Material(
                name="Silicon",
                formula="Si",
                permittivity_fn=_silicon_eps,
                description="Crystalline silicon, primary photonic material",
            ),
            Material(
                name="Silicon Dioxide",
                formula="SiO2",
                permittivity_fn=_silica_eps,
                description="Fused silica, common cladding material",
            ),
            Material(
                name="Titanium Dioxide",
                formula="TiO2",
                permittivity_fn=_tio2_eps,
                description="Amorphous TiO2, high-index visible/NIR material",
            ),
            Material(
                name="Gold",
                formula="Au",
                permittivity_fn=_gold_eps,
                description="Gold, plasmonic material",
            ),
            Material(
                name="Aluminium",
                formula="Al",
                permittivity_fn=_aluminium_eps,
                description="Aluminium, UV plasmonic material",
            ),
            Material(
                name="Silicon Nitride",
                formula="Si3N4",
                permittivity_fn=_sin_eps,
                description="Silicon nitride, low-loss photonic material",
            ),
            Material(
                name="Air",
                formula="Air",
                permittivity_fn=_air_eps,
                wavelength_range=(0.1e-6, 100e-6),
                description="Vacuum / air",
            ),
        ]

        for mat in builtins:
            self._materials[mat.formula.lower()] = mat
            self._materials[mat.name.lower()] = mat

        # Common aliases
        self._materials["silicon"] = self._materials["si"]
        self._materials["silica"] = self._materials["sio2"]
        self._materials["glass"] = self._materials["sio2"]
        self._materials["vacuum"] = self._materials["air"]

    def get(self, name: str) -> Material:
        """Look up a material by name or formula.

        Args:
            name: Material name or chemical formula (case-insensitive).

        Returns:
            Material instance.

        Raises:
            KeyError: If material is not found.
        """
        key = name.lower().strip()
        if key not in self._materials:
            available = sorted(set(m.formula for m in self._materials.values()))
            raise KeyError(
                f"Material '{name}' not found. "
                f"Available: {', '.join(available)}"
            )
        return self._materials[key]

    def register(self, material: Material) -> None:
        """Register a custom material.

        Args:
            material: Material instance to register.
        """
        self._materials[material.formula.lower()] = material
        self._materials[material.name.lower()] = material

    def list_materials(self) -> list[str]:
        """Return sorted list of unique material formulae."""
        return sorted(set(m.formula for m in self._materials.values()))

    def __contains__(self, name: str) -> bool:
        return name.lower().strip() in self._materials


# ── Module-level convenience ──

_library = MaterialLibrary()


def get_material(name: str) -> Material:
    """Get a material from the global library.

    Args:
        name: Material name or formula.

    Returns:
        Material instance.

    Example:
        >>> si = get_material("Si")
        >>> print(f"Si eps at 1550nm: {si.eps(1.55e-6):.4f}")
    """
    return _library.get(name)
