# PgBouncer Manager — Project Overview

## Workflow

This is a standalone project with a unified developer agent.

## Tech Stack

| Component | Stack |
|-----------|-------|
| Backend | FastAPI, Python 3.11 |
| CLI | Python CLI with argparse |
| Frontend | React 18, Vite, Tailwind |
| Infrastructure | Docker, Docker Compose, Kubernetes |

## Development Environment

```bash
# Backend
cd /path/to/pgbouncer-manager
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export CONFIG_DIR=/path/to/pgbouncer/config
uvicorn app.main:app --reload --port 3000

# Frontend
cd ui
npm run dev  # port 5173
```

## Commands

| Command | What it does |
|---------|--------------|
| `uvicorn app.main:app` | Start FastAPI server on port 3000 |
| `npm run dev` | Start Vite dev server on port 5173 |
| `npm run build` | Build production UI |
| `pytest` | Run Python tests |
| `ruff check .` | Run linter |
| `mypy .` | Run type checker |
| `mkdocs serve` | Preview docs locally |
| `mkdocs deploy` | Deploy docs to GitHub Pages |

## GitHub Actions

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `docs.yml` | Push to `docs/**` | Deploy to GitHub Pages |
| `test-lint.yml` | Push/PR | Python + Frontend CI |
| `release.yml` | Tag push (`v*`) | Create the GitHub release (gates the build) |
| `build.yml` | Release published | Build & push Docker image + PyPI package |

## Docker

```bash
docker build -t pgbouncer-manager .
docker run -p 3000:3000 \
  -e CONFIG_DIR=/app/config \
  -v ./pgbouncer/config:/app/config:ro \
  pgbouncer-manager
```

## API

- `GET /` - Health check
- `GET /tenants` - List tenants
- `POST /tenants` - Add tenant
- `GET /tenants/{id}` - Get tenant
- `PATCH /tenants/{id}` - Update tenant
- `DELETE /tenants/{id}` - Delete tenant
- `GET /pools/status` - Pool stats
- `GET /pools/stats` - Connection stats
- `POST /pools/reload` - Reload PgBouncer

## CLI

```bash
python -m cli.tenant tenant-add --id=tenant1 --host=db.example.com --password=secret
python -m cli.tenant tenant-list
python -m cli.tenant pools-list
python -m cli.tenant reload
```
