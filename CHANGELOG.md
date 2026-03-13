# Changelog

All notable changes to MetoSim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased] — V1 MVP

### Added
- Python SDK with Pydantic-validated simulation configs
- MetoSimClient for submitting and polling jobs
- Built-in material library (Si, SiO2, TiO2, Au, Al, Si3N4)
- FDTD solver core with Yee-grid implementation
- FastAPI REST API with job state machine
- HDF5 result writer with SHA-256 checksum verification
- Mesh generator for box, cylinder, sphere primitives
- plot_field() and plot_structure() visualization helpers
- API key authentication middleware
- Structured JSON logging with correlation IDs
- Docker Compose local development stack
- CI/CD pipelines (GitHub Actions)
- Single concurrent job enforcement (HTTP 409)
- Landing page for project documentation
