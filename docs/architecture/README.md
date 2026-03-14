# MetoSim Architecture

> Technical architecture documentation for the MetoSim platform.

---

## System Overview

MetoSim uses a **Hybrid Async API + GPU Workers** architecture (Option E from the ADR). The API and engine are separate deployable units sharing a lightweight Redis task broker.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                                                                 │
│   Researcher's Machine                                          │
│   ┌──────────────────────────────┐                              │
│   │  Python SDK (metosim)        │                              │
│   │  • Pydantic config validation│                              │
│   │  • Job polling + download    │                              │
│   │  • Checksum verification     │                              │
│   │  • plot_field() visualization│                              │
│   └──────────────┬───────────────┘                              │
│                  │ HTTPS + Bearer Token                          │
└──────────────────┼──────────────────────────────────────────────┘
                   │
┌──────────────────┼──────────────────────────────────────────────┐
│                  ▼     GATEWAY LAYER                            │
│   ┌──────────────────────────────┐    ┌──────────────────────┐  │
│   │  FastAPI REST API            │    │  PostgreSQL           │  │
│   │  • /v1/simulations (CRUD)    │◄──►│  • Job state (QUEUED, │  │
│   │  • API key auth middleware   │    │    RUNNING, COMPLETED,│  │
│   │  • Rate limiting             │    │    FAILED)            │  │
│   │  • Structured JSON logging   │    │  • API key hashes     │  │
│   │  • Correlation IDs           │    │  • Audit log          │  │
│   └──────────────┬───────────────┘    └──────────────────────┘  │
│                  │                                               │
│   Railway / Cloud Run (auto-scaled, stateless)                  │
└──────────────────┼──────────────────────────────────────────────┘
                   │ Redis Task Queue
┌──────────────────┼──────────────────────────────────────────────┐
│                  ▼     COMPUTE LAYER                            │
│   ┌──────────────────────────────┐                              │
│   │  Simulation Engine           │                              │
│   │  • Mesh generation           │                              │
│   │  • Material catalog          │                              │
│   │  • FDTD solver (JAX/NumPy)   │                              │
│   │  • PML boundaries            │                              │
│   │  • Convergence detection     │                              │
│   │  • HDF5 serialisation        │                              │
│   └──────────────┬───────────────┘                              │
│                  │                                               │
│   Modal / AWS EC2 G-series (B200 / A100 on-demand)             │
└──────────────────┼──────────────────────────────────────────────┘
                   │ Upload results
┌──────────────────┼──────────────────────────────────────────────┐
│                  ▼     STORAGE LAYER                            │
│   ┌──────────────────────────────┐                              │
│   │  S3-Compatible Object Store  │                              │
│   │  • HDF5 result files         │                              │
│   │  • SHA-256 checksums         │                              │
│   │  • Pre-signed download URLs  │                              │
│   │  • 90-day retention          │                              │
│   └──────────────────────────────┘                              │
│                                                                 │
│   AWS S3 / Cloudflare R2 / MinIO (local)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## End-to-End Data Flow

```
Step  Action                              Component
────  ────────────────────────────────    ─────────
 1    User creates Simulation(config)     SDK
 2    SDK validates with Pydantic         SDK
 3    SDK POSTs JSON to /v1/simulations   SDK → API
 4    API validates auth (Bearer token)   API
 5    API checks no active job (V1)       API → DB
 6    API creates job record (QUEUED)     API → DB
 7    API returns 202 + job_id            API → SDK
 8    API dispatches task to Redis         API → Redis
 9    Engine worker picks up task          Redis → Engine
10    Engine generates mesh from config    Engine
11    Engine runs FDTD solver              Engine (GPU)
12    Engine writes HDF5 + checksum        Engine
13    Engine uploads HDF5 to S3            Engine → S3
14    Engine updates job → COMPLETED       Engine → DB
15    SDK polls GET /simulations/{id}      SDK → API
16    SDK detects COMPLETED status         SDK
17    SDK requests result download URL     SDK → API
18    API returns pre-signed S3 URL        API → SDK
19    SDK streams HDF5, verifies SHA-256   SDK ← S3
20    User calls plot_field() on results   SDK
```

---

## Job State Machine

```
                    ┌──────────┐
                    │  QUEUED  │
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
              │    ┌─────▼─────┐   │
              │    │  RUNNING  │   │
              │    └─────┬─────┘   │
              │          │         │
              │    ┌─────┼─────┐   │
              │    │           │   │
         ┌────▼────▼──┐  ┌────▼───▼──┐
         │ COMPLETED  │  │  FAILED   │
         └────────────┘  └───────────┘
             (terminal)    (terminal)
```

**V1 Constraint:** Only one job may be in QUEUED or RUNNING state per API key at any time. Submitting while active returns `409 Conflict + Retry-After`.

---

## Component Details

### Python SDK (`sdk/metosim/`)

```
metosim/
├── __init__.py          # Public API surface
├── client.py            # MetoSimClient — HTTP client + job submission
├── simulation.py        # Pydantic models (SimulationConfig, Box, etc.)
├── job.py               # Job polling, wait(), results download
├── materials.py         # Material library (Si, SiO2, Au, etc.)
├── visualization.py     # plot_field(), plot_structure()
├── config.py            # SDK config (API URL, key, timeouts)
└── exceptions.py        # Exception hierarchy
```

### REST API (`api/app/`)

```
app/
├── main.py              # FastAPI app factory + lifespan
├── routers/
│   ├── simulations.py   # POST + GET /simulations
│   ├── results.py       # GET /simulations/{id}/results
│   └── health.py        # GET /health, /metrics
├── models/
│   ├── simulation.py    # Pydantic request/response schemas
│   └── job.py           # JobRecord with state machine
├── services/
│   ├── job_service.py   # Job lifecycle orchestration
│   └── auth_service.py  # Key generation + validation
├── middleware/
│   ├── auth.py          # Bearer token verification
│   └── logging.py       # Structured JSON + correlation IDs
└── db/
    ├── base.py          # Async SQLAlchemy engine
    └── job_repo.py      # Job CRUD repository (PostgreSQL)
```

### Simulation Engine (`engine/metosim_engine/`)

```
metosim_engine/
├── __init__.py
├── runner.py            # Entry point — config → mesh → solve → HDF5
├── solvers/
│   ├── fdtd.py          # 3D Yee-grid FDTD (JAX/NumPy)
│   ├── rcwa.py          # Stub — V2
│   └── fem.py           # Stub — V3+
├── mesh/
│   └── mesher.py        # Geometry → permittivity grid
├── materials/
│   └── catalog.py       # Server-side material database
└── io/
    └── hdf5_writer.py   # HDF5 serialisation + SHA-256
```

---

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| SDK | Python + Pydantic + httpx | Type-safe, async-ready, Jupyter-friendly |
| API | FastAPI + SQLAlchemy + Alembic | Auto OpenAPI docs, async, mature ORM |
| Task Queue | Redis + Celery | Simple broker, proven at scale |
| Engine | JAX / NumPy | GPU-accelerated arrays, NumPy fallback |
| Database | PostgreSQL | ACID transactions for job state |
| Storage | S3-compatible (R2/S3/MinIO) | Cheap, durable, pre-signed URLs |
| GPU | Modal (B200/A100) | On-demand, no idle cost |
| API Hosting | Railway / Cloud Run | Auto-scale, deploy-from-Git |
| CI/CD | GitHub Actions | Native, free for public repos |
| Monitoring | Prometheus + Grafana + Sentry | Metrics, dashboards, exception tracking |

---

## Security Model

```
Client ──TLS 1.3──► API ──TLS──► Engine
                     │
              API Key (SHA-256 hashed at rest)
              Pre-signed URLs (15-min expiry)
              Config sanitisation (no shell exec)
              Dependency scanning (pip-audit + Dependabot)
```

---

## Scaling Path

| Version | Architecture Change | Scaling Impact |
|---------|-------------------|----------------|
| V1 (MVP) | Single job per user | 1 concurrent simulation |
| V2 | Job queue + scheduler | N concurrent, priority-based |
| V3 | Batch API endpoint | 1000s of jobs, dataset generation |
| V4 | Iterative task chains | Adjoint loops for inverse design |

The Hybrid Async architecture supports all four versions without re-architecting. V2 = more Celery workers. V3 = batch task dispatch. V4 = chained tasks.
