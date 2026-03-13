"""MetoSim — Cloud-native meta-optics simulation platform.

Submit electromagnetic simulations to cloud GPUs through a clean Python API.

Example:
    >>> import metosim
    >>> client = metosim.MetoSimClient(api_key="your-key")
    >>> sim = metosim.Simulation(solver="fdtd", wavelength=1.55e-6, materials=["Si", "SiO2"])
    >>> job = client.run(sim)
    >>> results = job.results()
"""

__version__ = "1.0.0-dev"

from metosim.client import MetoSimClient
from metosim.config import Config, configure
from metosim.exceptions import (
    AuthenticationError,
    ChecksumMismatchError,
    JobFailedError,
    MetoSimError,
    SimulationConflictError,
    ValidationError,
)
from metosim.job import Job, JobStatus
from metosim.materials import Material, MaterialLibrary, get_material
from metosim.simulation import Simulation, SimulationConfig
from metosim.visualization import plot_field, plot_structure

__all__ = [
    # Core
    "MetoSimClient",
    "Simulation",
    "SimulationConfig",
    "Job",
    "JobStatus",
    # Configuration
    "Config",
    "configure",
    # Materials
    "Material",
    "MaterialLibrary",
    "get_material",
    # Visualization
    "plot_field",
    "plot_structure",
    # Exceptions
    "MetoSimError",
    "AuthenticationError",
    "ValidationError",
    "SimulationConflictError",
    "JobFailedError",
    "ChecksumMismatchError",
]
