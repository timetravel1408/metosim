# MetoSim User Manual

> **MetoSim** — Cloud-native electromagnetic simulation for nanophotonics and meta-optics.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Authentication](#3-authentication)
4. [Your First Simulation](#4-your-first-simulation)
5. [Defining Geometries](#5-defining-geometries)
6. [Materials](#6-materials)
7. [Sources and Excitation](#7-sources-and-excitation)
8. [Monitors](#8-monitors)
9. [Running Simulations](#9-running-simulations)
10. [Analysing Results](#10-analysing-results)
11. [Visualization](#11-visualization)
12. [Advanced Configuration](#12-advanced-configuration)
13. [Error Handling](#13-error-handling)
14. [Best Practices](#14-best-practices)
15. [Cookbook: Common Simulations](#15-cookbook-common-simulations)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. Introduction

MetoSim lets you run GPU-accelerated electromagnetic simulations from Python. You define structures, sources, and monitors locally — then submit to cloud GPUs for computation. Results come back as HDF5 files ready for analysis and publication.

**How it works:**

```
Your Python script
       ↓
  MetoSim SDK (validates config locally)
       ↓
  Cloud API (queues job, dispatches to GPU)
       ↓
  FDTD Engine (solves Maxwell's equations)
       ↓
  HDF5 results (downloaded + checksum-verified)
       ↓
  plot_field() (visualize locally)
```

**What you need:**
- Python 3.9 or later
- A MetoSim API key
- An internet connection

**What you don't need:**
- A local GPU
- COMSOL, CST, or any other license
- Infrastructure management skills

---

## 2. Installation

### From PyPI

```bash
pip install metosim
```

### From source (development)

```bash
git clone https://github.com/timetravel1408/metosim.git
cd metosim
pip install -e ".[dev]"
```

### Verify installation

```python
import metosim
print(metosim.__version__)  # "1.0.0-dev"
```

### Dependencies

Installed automatically:

| Package | Purpose |
|---------|---------|
| pydantic | Config validation |
| httpx | HTTP client |
| numpy | Array operations |
| h5py | HDF5 file I/O |
| matplotlib | Visualization |
| rich | Terminal output |
| tenacity | Retry logic |

---

## 3. Authentication

### Get your API key

Sign up at the [MetoSim Dashboard](https://dashboard.metosim.io) to generate your key.

### Configure the SDK

**Option A: Direct argument**
```python
client = metosim.MetoSimClient(api_key="mts_your_key_here")
```

**Option B: Environment variable (recommended)**
```bash
export METOSIM_API_KEY=mts_your_key_here
```
```python
client = metosim.MetoSimClient()  # picks up env var automatically
```

**Option C: Global configuration**
```python
metosim.configure(api_key="mts_your_key_here")
client = metosim.MetoSimClient()
```

### Verify connectivity

```python
print(client.health())
# {"status": "ok", "version": "1.0.0-dev", ...}
```

---

## 4. Your First Simulation

Here's a complete, minimal example — a silicon slab illuminated by a plane wave at 1550 nm:

```python
import metosim

# 1. Create client
client = metosim.MetoSimClient(api_key="mts_your_key")

# 2. Define a simple simulation
sim = metosim.Simulation(
    solver="fdtd",
    wavelength=1.55e-6,          # 1550 nm (telecom C-band)
    geometry=[
        metosim.Box(
            center=(0, 0, 0),
            size=(2e-6, 2e-6, 0.22e-6),  # 2μm × 2μm × 220nm slab
            material="Si",
        ),
    ],
    domain_size=(4e-6, 4e-6, 4e-6),
    resolution=20e-9,             # 20 nm grid
    time_steps=10000,
)

# 3. Submit to cloud GPU
print("Submitting simulation...")
job = client.run(sim)
print(f"Job ID: {job.job_id}")

# 4. Wait for completion (prints progress)
job.wait()

# 5. Download results
result_path = job.results(path="my_first_sim.hdf5")
print(f"Results saved to: {result_path}")

# 6. Visualize
metosim.plot_field(result_path, component="Ez")
```

**Expected output:**
```
Submitting simulation...
Job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  [  2.0s] Job a1b2c3d4... → QUEUED
  [ 15.3s] Job a1b2c3d4... → RUNNING
  [142.7s] Job a1b2c3d4... → COMPLETED
Results saved to: my_first_sim.hdf5
```

---

## 5. Defining Geometries

MetoSim supports three geometric primitives. Combine them to build complex photonic structures.

### Box (Rectangular slab)

```python
# Silicon waveguide core
waveguide = metosim.Box(
    center=(0, 0, 0),
    size=(10e-6, 0.5e-6, 0.22e-6),   # 10μm long, 500nm wide, 220nm tall
    material="Si",
)
```

### Cylinder (Nano-pillar or hole)

```python
# TiO2 nano-pillar for metasurface
pillar = metosim.Cylinder(
    center=(0, 0, 0),
    radius=0.15e-6,       # 150 nm radius
    height=0.6e-6,        # 600 nm tall
    axis="z",             # vertical pillar
    material="TiO2",
)
```

### Sphere (Nanoparticle)

```python
# Gold nanoparticle for plasmonics
particle = metosim.Sphere(
    center=(0, 0, 0),
    radius=50e-9,         # 50 nm radius
    material="Au",
)
```

### Combining structures

```python
sim = metosim.Simulation(
    geometry=[
        # SiO2 substrate
        metosim.Box(center=(0, 0, -0.5e-6), size=(4e-6, 4e-6, 1e-6), material="SiO2"),
        # Si waveguide on top
        metosim.Box(center=(0, 0, 0.11e-6), size=(10e-6, 0.5e-6, 0.22e-6), material="Si"),
        # TiO2 pillar on waveguide
        metosim.Cylinder(center=(0, 0, 0.52e-6), radius=0.1e-6, height=0.6e-6, material="TiO2"),
    ],
    wavelength=1.55e-6,
    domain_size=(12e-6, 4e-6, 4e-6),
)
```

Structures are painted onto the grid in list order — later structures overwrite earlier ones where they overlap.

---

## 6. Materials

### Built-in materials

| Formula | Name | n @ 1550 nm | Use Case |
|---------|------|-------------|----------|
| `Si` | Silicon | 3.476 | Waveguides, photonic crystals |
| `SiO2` | Silica | 1.444 | Cladding, substrates |
| `TiO2` | Titanium Dioxide | 2.270 | Metasurfaces (visible/NIR) |
| `Si3N4` | Silicon Nitride | 1.994 | Low-loss waveguides |
| `Au` | Gold | 0.56+11.2i | Plasmonics, nano-antennas |
| `Al` | Aluminium | 1.44+16.0i | UV plasmonics |
| `Air` | Air/Vacuum | 1.000 | Background |

### Looking up properties

```python
si = metosim.get_material("Si")
print(si.eps(1.55e-6))       # (12.08+0j)  — permittivity
print(si.n_at_1550nm)         # (3.476+0j)  — refractive index

# Works case-insensitive with aliases
metosim.get_material("silicon")   # same as "Si"
metosim.get_material("glass")     # same as "SiO2"
```

### Custom materials

```python
my_material = metosim.Material(
    name="PMMA",
    formula="PMMA",
    permittivity_fn=lambda wl: complex(1.49**2, 1e-4),
    wavelength_range=(0.4e-6, 2.0e-6),
)

# Register for use in simulations
lib = metosim.MaterialLibrary()
lib.register(my_material)
```

---

## 7. Sources and Excitation

Sources are configured inside `SimulationConfig` (advanced) or use defaults in `Simulation` (basic).

### Plane wave (default)

A uniform plane wave propagating along +z:

```python
from metosim.simulation import Source, PolarizationType

source = Source(
    source_type="plane_wave",
    wavelength=1.55e-6,
    polarization=PolarizationType.TE,
    direction=(0, 0, 1),
    amplitude=1.0,
)
```

### Gaussian beam

```python
source = Source(
    source_type="gaussian_beam",
    wavelength=0.633e-6,     # HeNe laser
    polarization=PolarizationType.TM,
)
```

### Mode source (waveguide)

```python
source = Source(
    source_type="mode_source",
    wavelength=1.55e-6,
    polarization=PolarizationType.TE,
    position=(1e-6, 0, 0),  # injection point
)
```

---

## 8. Monitors

Monitors record field or power data at specific locations during the simulation.

### Field monitor (2D plane)

Record all field components on the xy-plane at z = 0:

```python
xy_monitor = metosim.Monitor(
    name="field_xy_mid",
    monitor_type="field",
    center=(0, 0, 0),
    size=(4e-6, 4e-6, 0),   # zero z-extent → 2D slice
    components=["Ex", "Ey", "Ez"],
)
```

### Power monitor

Measure power flux through a plane:

```python
power_out = metosim.Monitor(
    name="transmitted_power",
    monitor_type="power",
    center=(0, 0, 2e-6),
    size=(4e-6, 4e-6, 0),
)
```

### Multiple monitors

```python
sim = metosim.Simulation(
    monitors=[
        metosim.Monitor(name="input", center=(0, 0, -1e-6), size=(4e-6, 4e-6, 0)),
        metosim.Monitor(name="output", center=(0, 0, 1e-6), size=(4e-6, 4e-6, 0)),
        metosim.Monitor(name="side_xz", center=(0, 0, 0), size=(4e-6, 0, 4e-6)),
    ],
    # ... rest of config
)
```

---

## 9. Running Simulations

### Submit and poll

```python
job = client.run(sim)          # returns immediately with job_id
job.wait(verbose=True)          # blocks until COMPLETED or FAILED
results = job.results()         # downloads HDF5
```

### Non-blocking workflow

```python
job = client.run(sim)
print(f"Submitted: {job.job_id}")

# Do other work...
import time
while not job.is_terminal:
    time.sleep(5)
    print(f"Status: {job.status}")

if job.status == metosim.JobStatus.COMPLETED:
    results = job.results()
```

### Resume a previous job

```python
# Save the job_id and come back later
job = client.get_job("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
if job.status == metosim.JobStatus.COMPLETED:
    results = job.results()
```

### Handle conflicts (V1 single-job limit)

```python
try:
    job = client.run(sim)
except metosim.SimulationConflictError as e:
    print(f"A job is already running. Retry in {e.retry_after}s")
```

---

## 10. Analysing Results

Results are stored as HDF5 files. You can work with them using `h5py` and `numpy` directly.

### Load results

```python
import h5py
import numpy as np

with h5py.File("results.hdf5", "r") as f:
    # Field data
    Ez = f["fields/Ez"][:]
    Hx = f["fields/Hx"][:]

    # Structure
    eps = f["structure/permittivity"][:]

    # Metadata
    config = f["metadata"].attrs["config"]
    wall_time = f["metadata"].attrs["wall_time"]
    converged = f["metadata"].attrs["converged"]

    # Convergence history
    steps = f["convergence/steps"][:]
    residuals = f["convergence/residuals"][:]

print(f"Field shape: {Ez.shape}")
print(f"Simulation took: {wall_time}s")
print(f"Converged: {converged}")
```

### Compute derived quantities

```python
# Field intensity
intensity = np.abs(Ez)**2 + np.abs(Ex)**2 + np.abs(Ey)**2

# Poynting vector (z-component)
Sz = np.real(Ex * np.conj(Hy) - Ey * np.conj(Hx))

# Transmission (ratio of output to input power)
# Through a plane at z=z_out vs z=z_in
T = np.sum(Sz[:, :, z_out]) / np.sum(Sz[:, :, z_in])
print(f"Transmission: {T:.4f} ({10*np.log10(T):.2f} dB)")
```

---

## 11. Visualization

### Quick field plot

```python
metosim.plot_field("results.hdf5", component="Ez")
```

### Customized plot

```python
metosim.plot_field(
    "results.hdf5",
    component="Ez",
    slice_axis="z",         # view xy-plane
    slice_index=50,          # at grid index 50
    cmap="RdBu_r",          # red-blue diverging colormap
    vmax=0.5,               # symmetric color scale
    figsize=(12, 8),
    title="Ez field at λ=1550nm",
    save_path="ez_field.png",
)
```

### Structure visualization

```python
metosim.plot_structure(
    "results.hdf5",
    slice_axis="z",
    cmap="coolwarm",
)
```

### Custom plots with matplotlib

```python
import h5py
import numpy as np
import matplotlib.pyplot as plt

with h5py.File("results.hdf5", "r") as f:
    Ez = f["fields/Ez"][:]
    eps = f["structure/permittivity"][:]

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Field
mid_z = Ez.shape[2] // 2
im0 = axes[0].imshow(Ez[:, :, mid_z].T, origin="lower", cmap="RdBu_r")
axes[0].set_title("Ez field")
plt.colorbar(im0, ax=axes[0])

# Structure
im1 = axes[1].imshow(np.real(eps[:, :, mid_z]).T, origin="lower", cmap="coolwarm")
axes[1].set_title("Permittivity εr")
plt.colorbar(im1, ax=axes[1])

plt.tight_layout()
plt.savefig("combined_plot.png", dpi=150)
plt.show()
```

---

## 12. Advanced Configuration

### Full Pydantic config

For maximum control, use `SimulationConfig` directly:

```python
from metosim.simulation import (
    SimulationConfig, SimulationDomain, Source, FDTDSettings,
    Box, Monitor, SolverType, BoundaryCondition, PolarizationType,
)

config = SimulationConfig(
    solver=SolverType.FDTD,
    domain=SimulationDomain(
        size=(8e-6, 8e-6, 4e-6),
        resolution=10e-9,
        boundary_conditions=(
            BoundaryCondition.PML,
            BoundaryCondition.PERIODIC,
            BoundaryCondition.PML,
        ),
        pml_layers=16,
    ),
    source=Source(
        source_type="plane_wave",
        wavelength=1.55e-6,
        polarization=PolarizationType.TE,
    ),
    structures=[
        Box(center=(0, 0, 0), size=(8e-6, 8e-6, 0.22e-6), material="Si"),
    ],
    monitors=[
        Monitor(name="reflection", center=(0, 0, -1e-6), size=(8e-6, 8e-6, 0)),
        Monitor(name="transmission", center=(0, 0, 1e-6), size=(8e-6, 8e-6, 0)),
    ],
    fdtd_settings=FDTDSettings(
        time_steps=50000,
        courant_factor=0.95,
        convergence_threshold=1e-7,
        check_every_n=500,
    ),
    metadata={"experiment": "periodic-slab", "doi": "10.xxxx/yyyy"},
)

# Wrap in Simulation for submission
sim = metosim.Simulation.__new__(metosim.Simulation)
sim.config = config
```

### Resolution guidelines

| Structure Feature | Recommended Resolution | Grid Points / λ |
|-------------------|----------------------|-----------------|
| Bulk dielectric | λ/(10n) | 10 |
| Waveguide mode | λ/(20n) | 20 |
| Metallic nanostructure | λ/(30n) | 30 |
| Plasmonic hotspot | λ/(40n) | 40+ |

Example: Silicon (n=3.48) at 1550 nm → feature size 220 nm → resolution ≤ 22 nm.

---

## 13. Error Handling

```python
import metosim

try:
    job = client.run(sim)
    job.wait(timeout=600)
    results = job.results()

except metosim.AuthenticationError:
    print("Check your API key")

except metosim.ValidationError as e:
    print(f"Config error: {e.message}")
    for err in e.validation_errors:
        print(f"  - {err}")

except metosim.SimulationConflictError as e:
    print(f"Job already running. Retry in {e.retry_after}s")

except metosim.JobFailedError as e:
    print(f"Simulation failed: {e.error_detail}")

except metosim.ChecksumMismatchError:
    print("Download corrupted — try again")

except metosim.TimeoutError as e:
    print(f"Timed out after {e.elapsed:.0f}s — job still running, use get_job() to check later")
```

---

## 14. Best Practices

### Start small, scale up

```python
# Development: coarse grid, few steps
sim_dev = metosim.Simulation(resolution=50e-9, time_steps=2000)

# Production: fine grid, full convergence
sim_prod = metosim.Simulation(resolution=10e-9, time_steps=50000)
```

### Use convergence, not fixed steps

The FDTD solver checks convergence every `check_every_n` steps. If the relative field change drops below `convergence_threshold`, the simulation stops early — saving GPU time and cost.

```python
from metosim.simulation import FDTDSettings

settings = FDTDSettings(
    time_steps=100000,            # upper bound
    convergence_threshold=1e-6,   # stop when converged
    check_every_n=500,            # check frequently
)
```

### Name your monitors

Clear names make post-processing easier:

```python
# Good
Monitor(name="transmission_1550nm", ...)
Monitor(name="reflection_plane", ...)

# Bad
Monitor(name="mon1", ...)
Monitor(name="m", ...)
```

### Store metadata

```python
sim = metosim.Simulation(
    metadata={
        "project": "metasurface-phase-control",
        "author": "Dr. Kumar",
        "wavelength_nm": 1550,
        "notes": "Sweep pillar radius 100-200nm",
    },
)
```

Metadata is embedded in the HDF5 file — your future self will thank you.

### Check convergence after simulation

```python
import h5py

with h5py.File("results.hdf5", "r") as f:
    converged = f["metadata"].attrs["converged"]
    steps = f["convergence/steps"][:]
    residuals = f["convergence/residuals"][:]

if not converged:
    print("WARNING: Simulation did not converge — increase time_steps")
    print(f"Final residual: {residuals[-1]:.2e}")
```

---

## 15. Cookbook: Common Simulations

### Thin-film interference (Fabry-Pérot)

```python
sim = metosim.Simulation(
    solver="fdtd",
    wavelength=0.633e-6,     # HeNe red
    geometry=[
        metosim.Box(
            center=(0, 0, 0),
            size=(2e-6, 2e-6, 0.5e-6),
            material="Si3N4",
        ),
    ],
    domain_size=(4e-6, 4e-6, 6e-6),
    resolution=15e-9,
    time_steps=30000,
    monitors=[
        metosim.Monitor(name="reflected", center=(0, 0, -2e-6), size=(4e-6, 4e-6, 0)),
        metosim.Monitor(name="transmitted", center=(0, 0, 2e-6), size=(4e-6, 4e-6, 0)),
    ],
)
```

### Plasmonic nanoparticle

```python
sim = metosim.Simulation(
    solver="fdtd",
    wavelength=0.532e-6,     # green laser
    geometry=[
        metosim.Sphere(center=(0, 0, 0), radius=40e-9, material="Au"),
    ],
    domain_size=(1e-6, 1e-6, 1e-6),
    resolution=5e-9,          # fine grid for metal
    time_steps=40000,
)
```

### Silicon waveguide

```python
sim = metosim.Simulation(
    solver="fdtd",
    wavelength=1.55e-6,
    geometry=[
        # SiO2 substrate (bottom half)
        metosim.Box(center=(0, 0, -1e-6), size=(12e-6, 4e-6, 2e-6), material="SiO2"),
        # Si waveguide core
        metosim.Box(center=(0, 0, 0.11e-6), size=(12e-6, 0.5e-6, 0.22e-6), material="Si"),
    ],
    domain_size=(14e-6, 4e-6, 4e-6),
    resolution=20e-9,
    time_steps=20000,
    monitors=[
        metosim.Monitor(name="input", center=(-5e-6, 0, 0), size=(0, 4e-6, 4e-6)),
        metosim.Monitor(name="output", center=(5e-6, 0, 0), size=(0, 4e-6, 4e-6)),
        metosim.Monitor(name="top_view", center=(0, 0, 0.11e-6), size=(14e-6, 4e-6, 0)),
    ],
)
```

### Dielectric metasurface unit cell

```python
sim = metosim.Simulation(
    solver="fdtd",
    wavelength=1.55e-6,
    geometry=[
        # SiO2 substrate
        metosim.Box(center=(0, 0, -0.25e-6), size=(0.6e-6, 0.6e-6, 0.5e-6), material="SiO2"),
        # TiO2 nano-pillar
        metosim.Cylinder(
            center=(0, 0, 0.3e-6),
            radius=0.12e-6,
            height=0.6e-6,
            material="TiO2",
        ),
    ],
    domain_size=(0.6e-6, 0.6e-6, 3e-6),
    resolution=10e-9,
    time_steps=30000,
)
# Use periodic boundary conditions for unit cell via SimulationConfig
```

---

## 16. Troubleshooting

### "API key required"

```python
# Fix: set your key
metosim.configure(api_key="mts_your_key")
# or
export METOSIM_API_KEY=mts_your_key
```

### "A simulation is already running" (409)

V1 allows one job at a time. Wait for it to finish or check:

```python
# Check your running job
job = client.get_job("previous-job-id")
print(job.status)
```

### "Connection refused"

```python
# Check API URL
metosim.configure(api_url="http://localhost:8000")  # local dev
metosim.configure(api_url="https://api.metosim.io")  # production
```

### Simulation doesn't converge

1. Increase `time_steps` (try 2× current value)
2. Lower `convergence_threshold` (e.g. `1e-5`)
3. Check your PML layers (increase if fields reach boundaries)
4. Verify resolution is fine enough for your materials

### Large HDF5 files

3D simulations can produce multi-GB files. Tips:

- Reduce `domain_size` to the minimum needed
- Use coarser `resolution` during development
- Record only the field components you need in monitors
- Results use gzip compression by default

### Import errors

```bash
# Missing h5py
pip install h5py

# Missing matplotlib
pip install matplotlib

# Full dev install
pip install metosim[dev]
```
