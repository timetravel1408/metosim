"""Unit tests for visualization helpers."""

import pytest


class TestPlotField:
    def test_import(self):
        from metosim.visualization import plot_field, plot_structure
        assert callable(plot_field)
        assert callable(plot_structure)
