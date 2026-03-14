# MetoSim SDK Reference

> Python SDK for the MetoSim cloud simulation platform.
> **Install:** `pip install metosim`

---

## Quick Start

```python
import metosim

client = metosim.MetoSimClient(api_key="mts_your_key")
sim = metosim.Simulation(solver="fdtd", wavelength=1.55e-6)
job = client.run(sim)
results = job.results()
metosim.plot_field(results, component="Ez")
```

---

## Configuration

### `metosim.configure(**kwargs) → Config`

Update global SDK settings. Values persist for the session.

```python
metosim.configure(
    api_key="mts_abc123",
    api_url="https://api.metosim.io",
    poll_interval=2.0,
    max_poll_time=3600.0,
    verify_checksums=True,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | str | `$METOSIM_API_KEY` | API key for authentication |
| `api_url` | str | `https://api.metosim.io` | API base URL |
| `api_version` | str | `v1` | API version prefix |
| `timeout` | float | `30.0` | HTTP request timeout (seconds) |
| `poll_interval` | float | `2.0` | Seconds between status polls |
| `max_poll_time` | float | `3600.0` | Max polling duration (seconds) |
| `verify_checksums` | bool | `True` | Verify HDF5 SHA-256 on download |

**Environment Variables**

The SDK checks these if arguments are not provided:

| Variable | Maps To |
|----------|---------|
| `METOSIM_API_KEY` | `api_key` |
| `METOSIM_API_URL` | `api_url` |
| `METOSIM_API_VERSION` | `api_version` |

---

## Client

### `metosim.MetoSimClient`

Primary entry point for interacting with the MetoSim platform.

```python
client = metosim.MetoSimClient(
    api_key="mts_abc123",    # or uses global config / env var
    api_url=None,             # override API URL
    config=None,              # explicit Config instance
)
```

#### `client.run(simulation) → Job`

Submit a simulation for GPU execution.

```python
sim = metosim.Simulation(solver="fdtd", wavelength=1.55e-6)
job = client.run(sim)
print(job.job_id)  # "a1b2c3d4-..."
```

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `AuthenticationError` | Invalid API key (401) |
| `SimulationConflictError` | Job already running (409) |
| `ValidationError` | Config rejected by API (422) |
| `MetoSimError` | Other API errors |

#### `client.get_job(job_id) → Job`

Retrieve an existing job by its UUID.

```python
job = client.get_job("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
print(job.status)
```

#### `client.health() → dict`

Check API connectivity and service health.

```python
>>> client.health()
{"status": "ok", "version": "1.0.0-dev", "db_connected": True, ...}
```

#### Context Manager

```python
with metosim.MetoSimClient(api_key="mts_abc123") as client:
    job = client.run(sim)
    results = job.results()
# HTTP client auto-closed
```

---

## Simulation

### `metosim.Simulation`

High-level simulation builder. Validates all parameters locally before API submission.

```python
sim = metosim.Simulation(
    solver="fdtd",
    wavelength=1.55e-6,
    materials=["Si", "SiO2"],
    geometry=[
        metosim.Box(center=(0, 0, 0), size=(1e-6, 1e-6, 0.22e-6), material="Si"),
        metosim.Sphere(center=(0, 0, 5e-7), radius=1e-7, material="TiO2"),
    ],
    domain_size=(4e-6, 4e-6, 4e-6),
    resolution=20e-9,
    time_steps=20000,
    monitors=[
        metosim.Monitor(name="center_xy", center=(0, 0, 0), size=(4e-6, 4e-6, 0)),
    ],
    metadata={"project": "my-experiment"},
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `solver` | str | `"fdtd"` | `"fdtd"`, `"rcwa"` (V2), `"fem"` (V3) |
| `wavelength` | float | `1.55e-6` | Operating wavelength in meters |
| `materials` | list[str] | `None` | Material names used |
| `geometry` | list or single | Default box | Geometry primitives |
| `domain_size` | tuple(3) | `(4e-6, 4e-6, 4e-6)` | Simulation domain (x, y, z) meters |
| `resolution` | float | `20e-9` | Grid cell size in meters |
| `time_steps` | int | `20000` | Maximum FDTD time steps |
| `monitors` | list[Monitor] | `[]` | Field/power monitors |
| `metadata` | dict | `{}` | Arbitrary metadata |

#### `sim.to_json() → str`

Serialise the simulation config to JSON.

#### `sim.config → SimulationConfig`

Access the underlying Pydantic model for advanced configuration.

---

## Geometry Primitives

All geometry objects require a `material` string matching a name in the material library.

### `metosim.Box`

Rectangular box.

```python
box = metosim.Box(
    center=(0, 0, 0),       # (x, y, z) in meters
    size=(1e-6, 1e-6, 0.22e-6),  # (dx, dy, dz) in meters
    material="Si",
)
```

### `metosim.Cylinder`

Cylindrical structure.

```python
cyl = metosim.Cylinder(
    center=(0, 0, 0),
    radius=0.5e-6,           # meters
    height=0.22e-6,           # meters
    axis="z",                 # "x", "y", or "z"
    material="Si",
)
```

### `metosim.Sphere`

Spherical structure.

```python
sph = metosim.Sphere(
    center=(0, 0, 5e-7),
    radius=1e-7,              # meters
    material="TiO2",
)
```

---

## Monitor

### `metosim.Monitor`

Field or power monitor for recording simulation data at specific planes.

```python
mon = metosim.Monitor(
    name="output_plane",
    monitor_type="field",      # "field", "power", or "mode"
    center=(0, 0, 1.5e-6),
    size=(4e-6, 4e-6, 0),     # zero in one axis → 2D plane
    components=["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"],
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | required | Unique label (1–64 chars) |
| `monitor_type` | str | `"field"` | `"field"`, `"power"`, `"mode"` |
| `center` | tuple(3) | `(0, 0, 0)` | Center position in meters |
| `size` | tuple(3) | `(0, 0, 0)` | Monitor extent; 0 → collapsed axis |
| `components` | list[str] | all 6 | Which field components to record |

---

## Job

### `metosim.Job`

Represents a submitted simulation. Returned by `client.run()`.

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `job.job_id` | str | UUID of the job |
| `job.status` | JobStatus | Current status (fetches from API) |
| `job.is_terminal` | bool | Whether in COMPLETED or FAILED state |
| `job.created_at` | str | ISO 8601 creation timestamp |
| `job.metadata` | dict | Server-returned metadata |

#### `job.wait(**kwargs) → Job`

Block until the job reaches a terminal state. Prints status updates.

```python
job.wait(
    poll_interval=2.0,   # seconds between polls (default: config)
    timeout=1800.0,      # max wait seconds (default: config)
    verbose=True,        # print progress (default: True)
)
```

**Raises:** `TimeoutError`, `JobFailedError`

#### `job.results(path=None, verify=None) → Path`

Download HDF5 results. Blocks and polls if the job is not yet complete.

```python
# Default: saves to ./{job_id}.hdf5
result_path = job.results()

# Custom path
result_path = job.results(path="output/my_results.hdf5")

# Skip checksum verification
result_path = job.results(verify=False)
```

**Raises:** `JobFailedError`, `ChecksumMismatchError`

### `metosim.JobStatus`

Enum of job states:

```python
JobStatus.QUEUED      # Waiting for GPU
JobStatus.RUNNING     # Solver executing
JobStatus.COMPLETED   # Results available
JobStatus.FAILED      # Error occurred
```

---

## Materials

### `metosim.get_material(name) → Material`

Look up a material from the built-in library.

```python
si = metosim.get_material("Si")
print(si.eps(1.55e-6))      # complex permittivity at 1550 nm
print(si.n_at_1550nm)        # refractive index at 1550 nm
```

Case-insensitive. Accepts formulas (`Si`, `SiO2`) or names (`Silicon`, `Glass`).

### `metosim.Material`

Material dataclass with wavelength-dependent permittivity.

```python
custom = metosim.Material(
    name="My Polymer",
    formula="PMMA",
    permittivity_fn=lambda wl: complex(1.49**2, 0),
    wavelength_range=(0.4e-6, 2.0e-6),
    description="PMMA polymer for visible/NIR",
)
```

#### `material.eps(wavelength) → complex`

Get complex permittivity at a given wavelength (meters).

#### `material.n_at_1550nm → complex`

Shortcut for refractive index at telecom C-band.

### `metosim.MaterialLibrary`

Registry of materials. Use for custom material management.

```python
lib = metosim.MaterialLibrary()
lib.register(custom_material)
mat = lib.get("PMMA")
print(lib.list_materials())  # ["Air", "Al", "Au", "PMMA", "Si", ...]
```

---

## Visualization

### `metosim.plot_field(results, component, **kwargs) → Figure | None`

Plot a 2D slice of an electromagnetic field component.

```python
metosim.plot_field(
    "results.hdf5",        # path or dict of arrays
    component="Ez",        # Ex, Ey, Ez, Hx, Hy, Hz
    slice_axis="z",        # axis perpendicular to slice
    slice_index=None,      # grid index (default: midpoint)
    freq_index=0,          # frequency index for multi-freq
    cmap="RdBu_r",         # matplotlib colormap
    vmax=None,             # symmetric color scale max
    figsize=(10, 6),       # figure size inches
    title=None,            # custom title
    save_path="fig.png",   # save to file
    show=True,             # display figure
)
```

### `metosim.plot_structure(results, **kwargs) → Figure | None`

Plot the permittivity distribution of the simulation structure.

```python
metosim.plot_structure(
    "results.hdf5",
    slice_axis="z",
    slice_index=None,
    cmap="coolwarm",
    figsize=(10, 6),
    show=True,
)
```

---

## Exceptions

All exceptions inherit from `MetoSimError`.

```python
from metosim import (
    MetoSimError,             # Base — catch-all
    AuthenticationError,      # 401 — bad/missing API key
    ValidationError,          # 422 — config rejected
    SimulationConflictError,  # 409 — job already running
    JobFailedError,           # Simulation failed on engine
    ChecksumMismatchError,    # HDF5 integrity failure
)
```

### Exception Attributes

**`MetoSimError`**

| Attribute | Type | Description |
|-----------|------|-------------|
| `.message` | str | Error message |
| `.details` | dict | Additional context |

**`SimulationConflictError`**

| Attribute | Type | Description |
|-----------|------|-------------|
| `.retry_after` | int | Suggested wait seconds |

**`JobFailedError`**

| Attribute | Type | Description |
|-----------|------|-------------|
| `.job_id` | str | Failed job UUID |
| `.error_detail` | str | Engine error message |

**`ChecksumMismatchError`**

| Attribute | Type | Description |
|-----------|------|-------------|
| `.expected` | str | Expected SHA-256 |
| `.actual` | str | Actual SHA-256 |

### Error Handling Pattern

```python
import metosim

try:
    job = client.run(sim)
    job.wait()
    results = job.results()
except metosim.SimulationConflictError as e:
    print(f"Busy — retry in {e.retry_after}s")
except metosim.JobFailedError as e:
    print(f"Simulation failed: {e.error_detail}")
except metosim.ChecksumMismatchError:
    print("Data integrity error — re-download")
except metosim.MetoSimError as e:
    print(f"Unexpected error: {e.message}")
```
