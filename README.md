# PgBouncer Manager

Manage PgBouncer tenants, pool sizes, and credentials with a FastAPI backend, CLI, and web interface.

## Features

- **FastAPI Backend** - RESTful API for tenant management
- **CLI** - Scriptable admin operations
- **React UI** - Visual tenant and pool monitoring
- **PgBouncer Integration** - Auto-reload configs via SIGHUP

## Architecture

```
pgbouncer-manager/
├── app/
│   ├── main.py          # FastAPI app entry point
│   └── routes/
│       ├── tenants.py   # Tenant CRUD endpoints
│       └── pools.py     # Pool monitoring endpoints
├── cli/
│   └── tenant.py        # CLI commands
├── ui/                  # React SPA (Vite)
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── hooks/       # Custom hooks
│   │   └── services/    # API services
│   └── package.json
├── requirements.txt
└── .gitignore
```

## Installation

### Prerequisites

- Python 3.11+
- Node.js 23+
- Docker (for PgBouncer integration)
- psql client

### Setup

```bash
# Backend
cd /root/Projects/Predicta/pgbouncer-manager
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# UI
cd ui
npm install
```

## Usage

### Start Backend

```bash
# Set environment variables
export CONFIG_DIR=/root/Projects/Predicta/predicta-infra/pgbouncer/config

# Run server
python -m uvicorn app.main:app --reload --port 3000
```

### Start UI

```bash
cd ui
npm run dev
```

The UI runs on `http://localhost:5173` and proxies `/api` to the backend.

### CLI

```bash
# Add a tenant
python -m cli.tenant tenant-add \
  --id=tenant1 \
  --host=db.example.com \
  --password=secret123

# List tenants
python -m cli.tenant tenant-list

# List pools
python -m cli.tenant pools-list

# Reload PgBouncer
python -m cli.tenant reload
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Health check |
| GET | /tenants | List all tenants |
| POST | /tenants | Add a new tenant |
| GET | /tenants/{id} | Get tenant details |
| PATCH | /tenants/{id} | Update tenant |
| DELETE | /tenants/{id} | Remove tenant |
| GET | /pools/status | List pool statistics |
| GET | /pools/stats | List connection statistics |
| POST | /pools/reload | Reload PgBouncer |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_DIR` | `/root/Projects/Predicta/predicta-infra/pgbouncer/config` | Path to PgBouncer config directory |
| `PORT` | `3000` | API server port |

## Docker

```bash
# Build
docker build -t pgbouncer-manager .

# Run
docker run -p 3000:3000 \
  -e CONFIG_DIR=/app/config \
  -v /path/to/pgbouncer/config:/app/config:ro \
  pgbouncer-manager
```
