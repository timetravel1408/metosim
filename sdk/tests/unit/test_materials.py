"""Unit tests for the material library."""

import numpy as np
import pytest

from metosim.materials import Material, MaterialLibrary, get_material


class TestMaterialLibrary:
    def test_silicon_eps_at_1550nm(self):
        si = get_material("Si")
        eps = si.eps(1.55e-6)
        assert np.real(eps) == pytest.approx(3.4757**2, rel=0.01)

    def test_silica_eps_at_1550nm(self):
        sio2 = get_material("SiO2")
        eps = sio2.eps(1.55e-6)
        n = np.sqrt(np.real(eps))
        assert n == pytest.approx(1.444, rel=0.01)

    def test_unknown_material_raises(self):
        with pytest.raises(KeyError, match="not found"):
            get_material("Unobtainium")

    def test_case_insensitive_lookup(self):
        si1 = get_material("Si")
        si2 = get_material("si")
        si3 = get_material("Silicon")
        assert si1.formula == si2.formula == si3.formula

    def test_alias_lookup(self):
        glass = get_material("glass")
        assert glass.formula == "SiO2"

    def test_custom_material_registered(self):
        lib = MaterialLibrary()
        custom = Material(
            name="MyMaterial",
            formula="MyMat",
            permittivity_fn=lambda wl: complex(4.0, 0.01),
        )
        lib.register(custom)
        retrieved = lib.get("MyMat")
        assert retrieved.eps(1.55e-6) == complex(4.0, 0.01)

    def test_list_materials(self):
        lib = MaterialLibrary()
        materials = lib.list_materials()
        assert "Si" in materials
        assert "SiO2" in materials
        assert "Au" in materials

    def test_n_at_1550nm_property(self):
        si = get_material("Si")
        n = si.n_at_1550nm
        assert np.real(n) == pytest.approx(3.4757, rel=0.01)
