"""MetoSim Simulation Engine — FDTD solver and supporting infrastructure."""

from metosim_engine.runner import run_simulation
from metosim_engine.solvers.fdtd import FDTDConfig, FDTDResult, FDTDSolver

__all__ = [
    "run_simulation",
    "FDTDSolver",
    "FDTDConfig",
    "FDTDResult",
]
