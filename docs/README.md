# PgBouncer Manager

Manage PgBouncer tenants, pool sizes, and credentials with a FastAPI backend, a
CLI, and a React web interface.

## Features

- **REST API** (FastAPI) — full CRUD for tenant management
- **CLI** — a thin HTTP client of the API for scripting
- **Web UI** — React + Vite dashboard for tenants and pool monitoring
- **Reload** — SIGHUP PgBouncer containers (or `RELOAD` via the admin console)
- **Hashed credentials** — passwords are stored as PgBouncer-compatible
  SCRAM-SHA-256 (default) or md5 hashes, never plaintext

## Architecture

```
pgbouncer-manager/
├── app/                 # FastAPI backend
│   ├── main.py          # App entry point (lifespan, CORS, routers)
│   ├── config.py        # pydantic-settings configuration
│   ├── auth.py          # md5 / SCRAM-SHA-256 hash generation
│   ├── deps.py          # FastAPI dependency providers
│   ├── routes/          # tenants, pools, capacity HTTP endpoints
│   └── services/        # PgBouncer service layer (file IO, psql, reload)
├── cli/                 # CLI tool (cli/tenant.py)
├── ui/                  # React SPA (Vite + Radix Themes)
└── docs/                # MkDocs documentation
```

## Prerequisites

- Python 3.11+
- Node.js 20+ (for the UI)
- `psql` client (for pool/stats queries against the admin console)
- Docker (optional, for SIGHUP-based reloads)

## Build and Run

```bash
# Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export CONFIG_DIR=/path/to/pgbouncer/config
uvicorn app.main:app --reload --port 3000

# Frontend
cd ui
npm install
npm run dev      # dev server on :5173, proxies /api -> :3000
```

## Configuration

All settings are environment variables (or a `.env` file). Common ones:

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_DIR` | `/etc/pgbouncer` | Directory holding `databases.ini` + `userlist.txt` |
| `AUTH_SCHEME` | `scram-sha-256` | Credential hash scheme (`scram-sha-256`, `md5`, `plain`) |
| `ADMIN_HOST` / `ADMIN_PORT` | `localhost` / `6432` | PgBouncer admin console |
| `ADMIN_USER` / `ADMIN_DB` | `pgbouncer` / `pgbouncer` | Admin console auth/db |
| `RELOAD_CONTAINERS` | `[]` | JSON list of Docker containers to SIGHUP on reload |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
| `SERVE_UI` | `true` | Serve the bundled web UI at `/`; set `false` for API-only |
| `CAPACITY_LIMITS` | `{}` | JSON map of `"host:port"` → `max_connections` |

## API Endpoints

All endpoints are namespaced under `/api`. The bundled UI, when present, is
served at `/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/tenants` | List all tenants |
| POST | `/api/tenants` | Add a new tenant |
| GET | `/api/tenants/{id}` | Get tenant details |
| PATCH | `/api/tenants/{id}` | Partially update a tenant |
| DELETE | `/api/tenants/{id}` | Remove a tenant |
| GET | `/api/pools/status` | Pool statistics (SHOW POOLS) |
| GET | `/api/pools/stats` | Connection statistics (SHOW STATS) |
| POST | `/api/pools/reload` | Reload PgBouncer |
| GET | `/api/capacity` | Connection budget per target Postgres |

## CLI Commands

The CLI talks to the running API (configure with `--api-url` or `PGBM_API_URL`).

```bash
python -m cli.tenant tenant-add \
  --id=mytenant --host=db.example.com --user=myuser \
  --password=mysecret --pool-size=20

python -m cli.tenant tenant-list
python -m cli.tenant tenant-update --id=mytenant --pool-size=25
python -m cli.tenant tenant-remove --id=mytenant
python -m cli.tenant pools-list
python -m cli.tenant reload
```

## Deployment

### Docker Compose

```yaml
services:
  pgbouncer-manager:
    build: .
    ports:
      - "3000:3000"
    environment:
      - CONFIG_DIR=/app/config
      - AUTH_SCHEME=scram-sha-256
    volumes:
      - ./pgbouncer-config:/app/config
```

See `docs/deployment/` for Kubernetes and bare-metal instructions.

## Contributing

1. Create a feature branch
2. Run tests: `pytest`
3. Lint and type-check: `ruff check .` and `mypy .`
4. Submit a pull request

## License

MIT
