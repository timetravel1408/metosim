# MetoSim API Reference

> **Base URL:** `https://api.metosim.io/v1`
> **Auth:** Bearer token in `Authorization` header
> **Content-Type:** `application/json`

---

## Authentication

All API requests require an API key passed as a Bearer token:

```
Authorization: Bearer mts_your_api_key_here
```

Unauthenticated requests return `401 Unauthorized`.

Get your API key from the [MetoSim Dashboard](https://dashboard.metosim.io).

---

## Endpoints

### Health Check

#### `GET /v1/health`

Check API and dependency health. **No authentication required.**

**Response `200 OK`**

```json
{
  "status": "ok",
  "version": "1.0.0-dev",
  "uptime_seconds": 3842.17,
  "db_connected": true,
  "redis_connected": true
}
```

---

#### `GET /v1/metrics`

Runtime metrics (Prometheus-compatible). **No authentication required.**

**Response `200 OK`**

```json
{
  "uptime_seconds": 3842.17,
  "version": "1.0.0-dev"
}
```

---

### Simulations

#### `POST /v1/simulations`

Submit a simulation for GPU execution. Returns `202 Accepted` with a `job_id` for polling.

**V1 Constraint:** Only one simulation can run at a time per API key. If a job is already active, returns `409 Conflict`.

**Request Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <api_key>` |
| `Content-Type` | Yes | `application/json` |
| `X-Correlation-ID` | No | Custom correlation ID for log tracing |

**Request Body**

```json
{
  "solver": "fdtd",
  "domain": {
    "size": [4e-6, 4e-6, 4e-6],
    "resolution": 20e-9,
    "boundary_conditions": ["pml", "pml", "pml"],
    "pml_layers": 12
  },
  "source": {
    "source_type": "plane_wave",
    "wavelength": 1.55e-6,
    "polarization": "te",
    "direction": [0.0, 0.0, 1.0],
    "amplitude": 1.0
  },
  "structures": [
    {
      "type": "box",
      "center": [0.0, 0.0, 0.0],
      "size": [1e-6, 1e-6, 2.2e-7],
      "material": "Si"
    },
    {
      "type": "sphere",
      "center": [0.0, 0.0, 5e-7],
      "radius": 1e-7,
      "material": "TiO2"
    }
  ],
  "monitors": [
    {
      "name": "field_xy",
      "monitor_type": "field",
      "center": [0.0, 0.0, 0.0],
      "size": [4e-6, 4e-6, 0.0],
      "components": ["Ex", "Ey", "Ez"]
    },
    {
      "name": "power_out",
      "monitor_type": "power",
      "center": [0.0, 0.0, 1.5e-6],
      "size": [4e-6, 4e-6, 0.0]
    }
  ],
  "fdtd_settings": {
    "time_steps": 20000,
    "courant_factor": 0.99,
    "convergence_threshold": 1e-6,
    "check_every_n": 1000
  },
  "metadata": {
    "project": "metasurface-v3",
    "notes": "Telecom C-band test"
  }
}
```

**Request Body Fields**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `solver` | string | Yes | — | Solver type: `fdtd` (V1), `rcwa` (V2), `fem` (V3+) |
| `domain` | object | Yes | — | Simulation domain definition |
| `domain.size` | [float, float, float] | Yes | — | Domain size (x, y, z) in meters |
| `domain.resolution` | float | No | `20e-9` | Grid cell size in meters |
| `domain.boundary_conditions` | [string, string, string] | No | `["pml","pml","pml"]` | Per-axis: `pml`, `periodic`, `bloch`, `symmetric`, `antisymmetric` |
| `domain.pml_layers` | int | No | `12` | Number of PML absorber layers (4–64) |
| `source` | object | Yes | — | Electromagnetic source configuration |
| `source.source_type` | string | No | `plane_wave` | `plane_wave`, `gaussian_beam`, `mode_source`, `dipole` |
| `source.wavelength` | float | Yes* | — | Wavelength in meters (*or `frequency`) |
| `source.frequency` | float | Yes* | — | Frequency in Hz (*or `wavelength`) |
| `source.polarization` | string | No | `te` | `te` or `tm` |
| `source.direction` | [float, float, float] | No | `[0,0,1]` | Propagation direction |
| `source.amplitude` | float | No | `1.0` | Source amplitude (> 0) |
| `structures` | array | Yes | — | List of geometry primitives (min 1) |
| `monitors` | array | No | `[]` | List of field/power monitors |
| `fdtd_settings` | object | No | auto | FDTD-specific solver settings |
| `fdtd_settings.time_steps` | int | No | `20000` | Max FDTD steps (100–1,000,000) |
| `fdtd_settings.courant_factor` | float | No | `0.99` | Courant stability factor (0–1.0) |
| `fdtd_settings.convergence_threshold` | float | No | `1e-6` | Relative field change for early stop |
| `fdtd_settings.check_every_n` | int | No | `1000` | Steps between convergence checks |
| `metadata` | object | No | `{}` | Arbitrary metadata stored with results |

**Geometry Types**

| Type | Required Fields | Optional Fields |
|------|----------------|-----------------|
| `box` | `center`, `size`, `material` | — |
| `cylinder` | `center`, `radius`, `height`, `material` | `axis` (default `z`) |
| `sphere` | `center`, `radius`, `material` | — |

**Response `202 Accepted`**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "QUEUED",
  "created_at": "2026-03-14T10:30:00Z",
  "message": "Simulation queued for execution"
}
```

**Error Responses**

| Status | Body | Condition |
|--------|------|-----------|
| `401 Unauthorized` | `{"detail": "Invalid or missing API key"}` | Bad or missing auth |
| `409 Conflict` | `{"detail": "A simulation is already running", "active_job_id": "...", "retry_after": 30}` | V1 concurrent job limit |
| `422 Unprocessable Entity` | `{"detail": [...]}` | Invalid simulation config |

The `409` response includes a `Retry-After` header (seconds).

---

#### `GET /v1/simulations/{job_id}`

Poll the status of a submitted simulation.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string (UUID) | Job ID from submission response |

**Response `200 OK`**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "COMPLETED",
  "created_at": "2026-03-14T10:30:00Z",
  "updated_at": "2026-03-14T10:32:45Z",
  "result_url": "https://storage.metosim.io/results/a1b2c3d4.hdf5",
  "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "error_detail": null,
  "metadata": {"project": "metasurface-v3"},
  "solver": "fdtd",
  "duration_seconds": 165.3
}
```

**Job Status Values**

| Status | Description |
|--------|-------------|
| `QUEUED` | Job received, waiting for GPU worker |
| `RUNNING` | Solver is executing on GPU |
| `COMPLETED` | Results available for download |
| `FAILED` | Solver error; see `error_detail` |

**State Machine**

```
QUEUED → RUNNING → COMPLETED
   │         │
   └─────────┴──→ FAILED
```

**Error Responses**

| Status | Condition |
|--------|-----------|
| `401 Unauthorized` | Bad or missing auth |
| `404 Not Found` | `job_id` does not exist |

---

#### `GET /v1/simulations/{job_id}/results`

Download simulation results. Redirects to a pre-signed S3 URL (15-minute expiry).

**Response `302 Found`**

Redirects to the HDF5 download URL. The SDK handles this automatically.

**Error Responses**

| Status | Condition |
|--------|-----------|
| `401 Unauthorized` | Bad or missing auth |
| `404 Not Found` | `job_id` does not exist |
| `409 Conflict` | Job not yet completed |

---

## HDF5 Result Format

Downloaded result files use the following HDF5 structure:

```
results.hdf5
├── fields/
│   ├── Ex          # 3D float64 array (Nx, Ny, Nz)
│   ├── Ey          # 3D float64 array
│   ├── Ez          # 3D float64 array
│   ├── Hx          # 3D float64 array
│   ├── Hy          # 3D float64 array
│   └── Hz          # 3D float64 array
├── structure/
│   └── permittivity  # 3D complex128 array (Nx, Ny, Nz)
├── convergence/
│   ├── steps        # 1D int array
│   └── residuals    # 1D float64 array
└── metadata/
    ├── @config             # JSON string of input config
    ├── @solver_version     # e.g. "metosim-engine-1.0.0-dev"
    ├── @created_at         # ISO 8601 timestamp
    ├── @sha256_checksum    # File integrity hash
    ├── @wall_time          # Simulation wall time (seconds)
    ├── @total_steps        # Actual steps simulated
    ├── @converged          # Boolean
    └── @performance        # Grid-points × steps / second
```

All field arrays use gzip compression (level 4) with chunking enabled.

---

## Materials Library

Built-in materials available for the `material` field in geometry structures:

| Name | Formula | n @ 1550 nm | Category |
|------|---------|-------------|----------|
| Silicon | `Si` | 3.476 | Semiconductor |
| Silicon Dioxide | `SiO2` | 1.444 | Dielectric |
| Titanium Dioxide | `TiO2` | 2.270 | High-index dielectric |
| Silicon Nitride | `Si3N4` | 1.994 | Dielectric |
| Gold | `Au` | 0.559 + 11.21i | Metal/Plasmonic |
| Aluminium | `Al` | 1.44 + 16.0i | Metal/Plasmonic |
| Air | `Air` | 1.000 | Background |

Case-insensitive lookup. Aliases: `glass` → `SiO2`, `vacuum` → `Air`, `silicon` → `Si`.

---

## Rate Limits

| Tier | Submissions/min | Concurrent Jobs | Max Steps |
|------|----------------|-----------------|-----------|
| Free | 5 | 1 | 50,000 |
| Pro | 30 | 5 (V2) | 1,000,000 |

Rate-limited requests return `429 Too Many Requests` with a `Retry-After` header.

---

## Error Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message",
  "error_code": "OPTIONAL_ERROR_CODE"
}
```

**Common Error Codes**

| HTTP | Code | Meaning |
|------|------|---------|
| 401 | `AUTH_INVALID` | API key invalid or expired |
| 409 | `JOB_CONFLICT` | Concurrent job limit reached |
| 422 | `VALIDATION_ERROR` | Config failed Pydantic validation |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |

---

## Response Headers

All responses include:

| Header | Description |
|--------|-------------|
| `X-Correlation-ID` | Request trace ID (pass your own or auto-generated) |
| `X-Response-Time-Ms` | Server-side processing time |
| `Retry-After` | Seconds to wait (on 409/429 responses) |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0-dev | March 2026 | Initial MVP — FDTD, single-job, HDF5 results |
