# MetoSim — Meta-Optics Simulation Platform

> Cloud-native electromagnetic simulation for nanophotonics and metasurface design.

[![CI](https://github.com/metosim/metosim/actions/workflows/ci.yml/badge.svg)](https://github.com/metosim/metosim/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

## Overview

MetoSim is the simulation pillar of the **Meto Platform** triad:

| Component | Purpose |
|-----------|---------|
| **MetoSim** | Simulation & computational design |
| **MetoFab** | Nanofabrication workflows |
| **MetoLab** | Experimental prototyping |

Researchers interact through a Python SDK while GPU-accelerated FDTD computation executes on cloud infrastructure.

## Quick Start

```bash
pip install metosim
```

```python
import metosim

# Configure client
client = metosim.MetoSimClient(api_key="your-key")

# Define simulation
sim = metosim.Simulation(
    solver="fdtd",
    wavelength=1.55e-6,
    materials=["Si", "SiO2"],
    geometry=my_structure,
)

# Submit to cloud GPU
job = client.run(sim)

# Poll and retrieve
results = job.results()
metosim.plot_field(results, component="Ez")
```

## Architecture

```
SDK ──HTTPS──▶ FastAPI ──Redis──▶ GPU Engine
                 │                    │
              PostgreSQL          S3 (HDF5)
```

- **SDK**: Python client with Pydantic validation
- **API**: FastAPI gateway with auth & job state machine
- **Engine**: JAX/NumPy FDTD solver on Modal GPU workers
- **Storage**: S3-compatible object store for HDF5 results

## Repository Structure

```
metosim/
├── sdk/          # Python SDK (pip install metosim)
├── api/          # FastAPI REST API
├── engine/       # FDTD simulation engine
├── infra/        # Terraform, K8s, Docker Compose
├── docs/         # Architecture docs & tutorials
└── .github/      # CI/CD workflows
```

## Development

```bash
# Clone and setup
git clone https://github.com/metosim/metosim.git
cd metosim

# Start local services
docker compose -f infra/docker-compose.yml up -d

# Install SDK in dev mode
pip install -e ".[dev]"

# Run tests
pytest --cov
```

## Roadmap

| Version | Target | Features |
|---------|--------|----------|
| **V1** (Now) | MVP | Single-job FDTD, Python SDK, HDF5 results |
| **V2** (Q2 2026) | Batch | Parameter sweeps, RCWA, concurrent jobs |
| **V3** (Q3 2026) | ML | Dataset generation, batch export |
| **V4** (Q4 2026) | Inverse | Adjoint solver, AI-guided design |

## Team

- **Dr. Abhishek Kumar** — Principal Investigator
- **Kishan** — Strategy & Software Architecture

## License

Proprietary — All rights reserved. See [LICENSE](LICENSE) for details.
