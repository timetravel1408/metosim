# MetoSim — Deployment Guide

## Prerequisites

- **Docker Desktop** (v4.0+) — [Install](https://docs.docker.com/get-docker/)
- **Git** — [Install](https://git-scm.com/downloads)
- **Python 3.9+** — for running the SDK locally
- **Railway CLI** (for cloud deploy) — `npm install -g @railway/cli`

---

## Part 1 — Local Development (Docker Compose)

### Step 1: Clone and enter the repo

```bash
git clone https://github.com/timetravel1408/metosim.git
cd metosim
```

### Step 2: Create your `.env` file

```bash
cp .env.example .env
```

No changes needed for local dev — defaults point to Docker services.

### Step 3: Start all services

```bash
docker compose -f infra/docker-compose.yml up --build
```

This spins up **4 containers**:

| Service | Port | Purpose |
|---------|------|---------|
| **API** | `localhost:8000` | FastAPI server with hot reload |
| **PostgreSQL** | `localhost:5432` | Job state database |
| **Redis** | `localhost:6379` | Task queue broker |
| **MinIO** | `localhost:9000` | S3-compatible object storage |

MinIO console is at `localhost:9001` (login: `minioadmin` / `minioadmin`).

### Step 4: Verify everything is running

```bash
# Health check
curl http://localhost:8000/v1/health

# Expected response:
# {"status":"ok","version":"1.0.0-dev","uptime_seconds":...,"db_connected":true,"redis_connected":true}
```

API docs (Swagger UI): **http://localhost:8000/docs**

### Step 5: Test with the Python SDK

```bash
# In a new terminal, install the SDK
cd metosim
pip install -e ".[dev]"
```

```python
import metosim

# Point SDK at local API
metosim.configure(
    api_key="test-key-12345678",
    api_url="http://localhost:8000",
)

client = metosim.MetoSimClient()

# Check API health
print(client.health())

# Submit a simulation
sim = metosim.Simulation(
    solver="fdtd",
    wavelength=1.55e-6,
    domain_size=(2e-6, 2e-6, 2e-6),
    resolution=50e-9,
    time_steps=1000,
)
job = client.run(sim)
print(f"Job submitted: {job.job_id}")
print(f"Status: {job.status}")
```

### Step 6: Run tests

```bash
# Unit tests (no services needed)
pytest sdk/tests/unit/ -v
pytest api/tests/unit/ -v
pytest engine/tests/unit/ -v

# All tests
pytest --cov -v
```

### Useful Docker commands

```bash
# Start in background
docker compose -f infra/docker-compose.yml up -d --build

# View logs
docker compose -f infra/docker-compose.yml logs -f api

# Stop everything
docker compose -f infra/docker-compose.yml down

# Stop and wipe all data (fresh start)
docker compose -f infra/docker-compose.yml down -v

# Rebuild only the API container
docker compose -f infra/docker-compose.yml up -d --build api
```

---

## Part 2 — Cloud Deployment (Railway)

Railway gives you a managed PostgreSQL, Redis, and auto-deployed API from your GitHub repo.

### Step 1: Create a Railway account

Go to [railway.app](https://railway.app) and sign up with GitHub.

### Step 2: Install Railway CLI

```bash
npm install -g @railway/cli
railway login
```

### Step 3: Create a new project

```bash
cd metosim
railway init
```

Select **"Empty Project"** when prompted.

### Step 4: Add PostgreSQL

```bash
railway add --plugin postgresql
```

Or in the Railway dashboard: **New** → **Database** → **PostgreSQL**.

Railway auto-sets `DATABASE_URL` in your environment.

### Step 5: Add Redis

```bash
railway add --plugin redis
```

Or dashboard: **New** → **Database** → **Redis**.

Railway auto-sets `REDIS_URL`.

### Step 6: Set environment variables

In the Railway dashboard, go to your **API service** → **Variables**:

```
S3_ENDPOINT_URL=https://your-s3-endpoint.com
S3_ACCESS_KEY=your-key
S3_SECRET_KEY=your-secret
S3_BUCKET_NAME=metosim-results
METOSIM_SECRET_KEY=generate-a-random-string-here
LOG_LEVEL=INFO
DEBUG=false
```

For object storage, you can use:
- **Cloudflare R2** (free 10GB, S3-compatible) — recommended
- **AWS S3**
- **Railway Volume** (simplest for MVP)

### Step 7: Deploy the API

```bash
railway up
```

Railway reads `railway.toml`, builds the Docker image, and deploys.

Or connect your GitHub repo in the dashboard for **auto-deploy on push**:

1. Dashboard → **New** → **GitHub Repo** → Select `timetravel1408/metosim`
2. Set **Root Directory**: `/` 
3. Railway detects `railway.toml` and uses the API Dockerfile

### Step 8: Get your public URL

```bash
railway domain
```

This generates a URL like `metosim-production.up.railway.app`.

Test it:

```bash
curl https://metosim-production.up.railway.app/v1/health
```

### Step 9: Point SDK at production

```python
import metosim

metosim.configure(
    api_key="your-production-api-key",
    api_url="https://metosim-production.up.railway.app",
)

client = metosim.MetoSimClient()
print(client.health())
```

---

## Part 3 — Setting up Object Storage (Cloudflare R2)

R2 is the easiest S3-compatible storage for results. Free tier: 10GB storage, 10M requests/month.

### Step 1: Create R2 bucket

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → R2
2. Create bucket: `metosim-results`
3. Create API token with read/write access

### Step 2: Add R2 credentials to Railway

```
S3_ENDPOINT_URL=https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
S3_ACCESS_KEY=your-r2-access-key
S3_SECRET_KEY=your-r2-secret-key
S3_BUCKET_NAME=metosim-results
S3_REGION=auto
```

---

## Part 4 — GPU Engine Deployment (Modal)

The FDTD engine needs GPUs. Modal is the simplest way to get on-demand B200/A100.

### Step 1: Create Modal account

Go to [modal.com](https://modal.com) and sign up.

```bash
pip install modal
modal token new
```

### Step 2: Create Modal app (future)

```python
# engine/modal_app.py (to be implemented)
import modal

app = modal.App("metosim-engine")

@app.function(gpu="B200", timeout=3600)
def run_fdtd(config: dict) -> dict:
    from metosim_engine.runner import run_simulation
    return run_simulation(config)
```

For V1 MVP, the engine runs as a stub — simulations are dispatched but the actual GPU execution is wired in Sprint S4 (Integration). The API, job state machine, and SDK work end-to-end right now.

---

## Architecture Summary

```
LOCAL DEV                           PRODUCTION (Railway + Modal)
─────────                           ───────────────────────────

 SDK (your machine)                  SDK (researcher's machine)
   │                                   │
   ▼                                   ▼
 API (localhost:8000)                API (Railway auto-scaled)
   │         │                         │         │
   ▼         ▼                         ▼         ▼
 Postgres  Redis                     Postgres  Redis
 (:5432)   (:6379)                   (Railway) (Railway)
              │                                   │
              ▼                                   ▼
           MinIO (:9000)                       Modal GPU
              │                                   │
              ▼                                   ▼
           HDF5 files                        Cloudflare R2
```

---

## Cost Estimate (Railway)

| Resource | Free Tier | Paid |
|----------|-----------|------|
| API (Hobby) | 500 hrs/month | $5/month |
| PostgreSQL | 1 GB | $5/month |
| Redis | 50 MB | $5/month |
| **Total MVP** | **$0** (trial) | **~$15/month** |

GPU costs (Modal) only apply when simulations actually run — approximately $2–4/hour for B200.

---

## Troubleshooting

**Docker: "port already in use"**
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

**Docker: API can't connect to Postgres**
```bash
# Ensure Postgres is healthy first
docker compose -f infra/docker-compose.yml ps
# Rebuild if needed
docker compose -f infra/docker-compose.yml down -v && docker compose -f infra/docker-compose.yml up --build
```

**Railway: Build fails**
```bash
# Check logs
railway logs
# Ensure railway.toml is committed
git add railway.toml && git commit -m "add railway config" && git push
```

**SDK: Connection refused**
```python
# Make sure api_url matches your deployment
metosim.configure(api_url="http://localhost:8000")  # local
metosim.configure(api_url="https://your-app.up.railway.app")  # production
```
