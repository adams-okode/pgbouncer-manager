# PgBouncer Manager

Manage PgBouncer tenants, pool sizes, and credentials with a FastAPI backend, CLI, and React UI.

**Live Demo:** `https://adams-okode.github.io/pgbouncer-manager/`  
**API Docs:** `http://localhost:3000/docs` (Swagger UI)

## What It Does

This tool manages multi-tenant PgBouncer deployments by:

1. **Dynamic Tenant Management** - Add/remove tenants via API/CLI without restart
2. **Pool Configuration** - Adjust pool sizes per tenant dynamically
3. **Credential Rotation** - Securely rotate tenant database passwords
4. **PgBouncer Reload** - Send SIGHUP to reload configs without downtime
5. **Pool Monitoring** - Real-time pool statistics and connection metrics

## Architecture

```
pgbouncer-manager/
├── app/              # FastAPI backend
│   ├── main.py       # App entry point
│   └── routes/       # API endpoints
├── cli/              # CLI tool (tenant.py)
├── ui/               # React SPA (Vite)
└── docs/             # MkDocs documentation
```

## Quick Start

```bash
# 1. Start backend
cd /path/to/pgbouncer-manager
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export CONFIG_DIR=/path/to/pgbouncer/config
uvicorn app.main:app --reload --port 3000

# 2. Start UI (separate terminal)
cd ui && npm install && npm run dev

# 3. Add a tenant
curl -X POST http://localhost:3000/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "id": "tenant1",
    "host": "db.example.com",
    "password": "secret123",
    "pool_size": 15
  }'

# 4. Check pools
curl http://localhost:3000/pools/status
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET /` | Health check |
| `GET /tenants` | List all tenants |
| `POST /tenants` | Add a new tenant |
| `PATCH /tenants/{id}` | Update tenant (pool_size, password) |
| `DELETE /tenants/{id}` | Remove tenant |
| `GET /pools/status` | Pool statistics (active, waiting, idle) |
| `GET /pools/stats` | Connection statistics |
| `POST /pools/reload` | Reload PgBouncer via SIGHUP |

## CLI Commands

```bash
# Add tenant
python -m cli.tenant tenant-add \
  --id=tenant1 --host=db.example.com --password=secret123

# List tenants
python -m cli.tenant tenant-list

# Update pool size
python -m cli.tenant tenant-update --id=tenant1 --pool-size=20

# Remove tenant
python -m cli.tenant tenant-remove --id=tenant1

# List pools
python -m cli.tenant pools-list

# Reload PgBouncer
python -m cli.tenant reload
```

## Docker

```bash
docker build -t pgbouncer-manager .
docker run -p 3000:3000 \
  -e CONFIG_DIR=/app/config \
  -v /path/to/pgbouncer/config:/app/config:ro \
  pgbouncer-manager
```

## Documentation

See `docs/` for:
- API reference
- CLI usage
- Deployment (Docker, Kubernetes, Bare Metal)
- Security best practices
- Contributing guidelines

## CI/CD

- **Docs**: Auto-deploy to GitHub Pages on `docs/**` changes
- **Tests**: pytest + ruff + mypy + frontend linting
- **Docker**: Build & push images to Docker Hub
- **Releases**: Auto-generate GitHub releases on tags
