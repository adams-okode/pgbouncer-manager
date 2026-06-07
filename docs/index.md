# PgBouncer Manager

Manage PgBouncer tenants, pool sizes, and credentials with a FastAPI backend, CLI, and web interface.

## Features

- **FastAPI Backend** - RESTful API for tenant management
- **CLI** - Scriptable admin operations
- **React UI** - Visual tenant and pool monitoring
- **PgBouncer Integration** - Auto-reload configs via SIGHUP

## Quick Start

```bash
# Backend
export CONFIG_DIR=/root/Projects/Predicta/predicta-infra/pgbouncer/config
python -m uvicorn app.main:app --reload --port 3000

# UI
cd ui && npm run dev
```

## Documentation

- [API Reference](api.md)
- [CLI](cli.md)
- [Deployment](deployment/docker.md)
- [Security](security.md)
