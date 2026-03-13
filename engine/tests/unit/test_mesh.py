"""Unit tests for mesh generation and HDF5 I/O."""

import numpy as np
import pytest


class TestMeshGeneration:
    def test_box_mesh(self):
        from metosim_engine.mesh.mesher import generate_mesh

        grid = generate_mesh(
            grid_shape=(20, 20, 20),
            resolution=1.0,
            structures=[{
                "type": "box",
                "center": (10, 10, 10),
                "size": (6, 6, 6),
                "material": "Si",
            }],
            material_catalog={"Si": complex(12.0, 0)},
            background_eps=1.0,
        )
        assert grid.shape == (20, 20, 20)
        assert np.real(grid[10, 10, 10]) == pytest.approx(12.0)
        assert np.real(grid[0, 0, 0]) == pytest.approx(1.0)

    def test_sphere_mesh(self):
        from metosim_engine.mesh.mesher import generate_mesh

        grid = generate_mesh(
            grid_shape=(20, 20, 20),
            resolution=1.0,
            structures=[{
                "type": "sphere",
                "center": (10, 10, 10),
                "radius": 3,
                "material": "Au",
            }],
            material_catalog={"Au": complex(-100, 10)},
        )
        # Center should be gold
        assert np.real(grid[10, 10, 10]) == pytest.approx(-100)
        # Corner should be background
        assert np.real(grid[0, 0, 0]) == pytest.approx(1.0)

    def test_empty_structures(self):
        from metosim_engine.mesh.mesher import generate_mesh

        grid = generate_mesh(
            grid_shape=(5, 5, 5),
            resolution=1.0,
            structures=[],
            material_catalog={},
            background_eps=2.25,
        )
        assert np.all(np.real(grid) == pytest.approx(2.25))
