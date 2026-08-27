# PgBouncer Manager — Project Overview

## Workflow

This is a standalone project with a unified developer agent.
See `CLAUDE.md` for contribution rules (commit conventions, release process).

## Tech Stack

| Component | Stack |
|-----------|-------|
| Backend | FastAPI, Python 3.11 |
| CLI | Python CLI with argparse |
| Frontend | React 18, Vite, Radix Themes |
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
| `release.yml` | Push to `main` | release-please: version PR, then tag + GitHub release + publish |
| `build.yml` | Called by `release.yml` (or manual) | Build & push the multi-arch Docker image |

## Docker

```bash
docker build -t pgbouncer-manager .
docker run -p 3000:3000 \
  -e CONFIG_DIR=/app/config \
  -v ./pgbouncer/config:/app/config:ro \
  pgbouncer-manager
```

## API

All endpoints are namespaced under `/api`; the bundled SPA is served at `/`.

- `GET /api/health` - Health check
- `GET /api/tenants` - List tenants
- `POST /api/tenants` - Add tenant
- `GET /api/tenants/{id}` - Get tenant
- `PATCH /api/tenants/{id}` - Update tenant
- `DELETE /api/tenants/{id}` - Delete tenant
- `GET /api/pools/status` - Pool stats
- `GET /api/pools/stats` - Connection stats
- `POST /api/pools/reload` - Reload PgBouncer
- `GET /api/capacity` - Connection budget per target Postgres

## CLI

```bash
python -m cli.tenant tenant-add --id=tenant1 --host=db.example.com --password=secret
python -m cli.tenant tenant-list
python -m cli.tenant pools-list
python -m cli.tenant reload
```
