# PgBouncer Manager

Manage PgBouncer tenants, pool sizes, and credentials over a REST API, a CLI,
and a web UI — without hand-editing `databases.ini` and `userlist.txt`.

This image bundles the FastAPI backend and the compiled React UI. It does **not**
contain PgBouncer; it manages a PgBouncer running elsewhere by writing that
config directory and reloading it.

- **Source & full docs:** https://github.com/adams-okode/pgbouncer-manager

## Tags

| Tag | Meaning |
|-----|---------|
| `latest` | Most recent release |
| `2.1.0` | Exact version — use this in production |
| `2.1` | Latest patch of the 2.1 series |

Built for `linux/amd64` and `linux/arm64`.

## How it works

The manager and PgBouncer **must share a config directory**. That is the entire
integration: the manager writes `databases.ini` / `userlist.txt`, then tells
PgBouncer to reload.

```
client ──▶ pgbouncer:6432 ──▶ postgres:5432
               ▲ reads /etc/pgbouncer/{databases.ini,userlist.txt}
               │
 manager:3000 ─┘ writes those files, then RELOADs via the admin console
```

Mount that directory **read-write** into the manager. Mounting it read-only
will make every write fail.

## Quick start

```bash
docker run -d --name pgbouncer-manager \
  -p 3000:3000 \
  -v pgbconf:/etc/pgbouncer \
  -e CONFIG_DIR=/etc/pgbouncer \
  -e ADMIN_HOST=pgbouncer \
  adamsokode/pgbouncer-manager:2.1.0
```

UI on <http://localhost:3000>, API under `/api`.

## Docker Compose

```yaml
services:
  pgbouncer:
    image: edoburu/pgbouncer:latest
    volumes:
      - pgbconf:/etc/pgbouncer
    ports:
      - "6432:6432"

  manager:
    image: adamsokode/pgbouncer-manager:2.1.0
    depends_on: [pgbouncer]
    environment:
      CONFIG_DIR: /etc/pgbouncer
      AUTH_SCHEME: scram-sha-256
      ADMIN_HOST: pgbouncer
      ADMIN_PORT: "6432"
      CAPACITY_LIMITS: '{"postgres:5432": 200}'
    volumes:
      - pgbconf:/etc/pgbouncer      # read-write: the manager edits these files
    ports:
      - "3000:3000"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:3000/api/health').status==200 else 1)\""]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  pgbconf:
```

A complete runnable stack — PgBouncer plus a real Postgres, with an end-to-end
test — is in [`examples/`](https://github.com/adams-okode/pgbouncer-manager/tree/main/examples).

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_DIR` | `/etc/pgbouncer` | Directory holding `databases.ini` + `userlist.txt` |
| `AUTH_SCHEME` | `scram-sha-256` | Credential hashing (`scram-sha-256`, `md5`, `plain`) |
| `ADMIN_HOST` | `localhost` | PgBouncer admin console host |
| `ADMIN_PORT` | `6432` | PgBouncer admin console port |
| `ADMIN_USER` | `pgbouncer` | Admin console user |
| `ADMIN_DB` | `pgbouncer` | Admin console database |
| `RELOAD_CONTAINERS` | `[]` | JSON list of Docker containers to SIGHUP. Empty ⇒ `RELOAD` over the admin console |
| `CAPACITY_LIMITS` | `{}` | JSON map of `"host:port"` → `max_connections`, used to compute headroom |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
| `SERVE_UI` | `true` | Serve the bundled UI at `/`; set `false` for API-only |

## Health checks

Probe **`/api/health`**, not `/`. The UI is mounted at `/` as a catch-all and
answers even when the API is broken, so `/` cannot detect a dead backend.

```yaml
livenessProbe:
  httpGet:
    path: /api/health
    port: 3000
```

## API

All endpoints are namespaced under `/api`; the UI is served at `/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/tenants` | List tenants |
| POST | `/api/tenants` | Add a tenant |
| GET | `/api/tenants/{id}` | Get a tenant |
| PATCH | `/api/tenants/{id}` | Update a tenant |
| DELETE | `/api/tenants/{id}` | Remove a tenant |
| GET | `/api/pools/status` | Pool statistics (`SHOW POOLS`) |
| GET | `/api/pools/stats` | Connection statistics (`SHOW STATS`) |
| POST | `/api/pools/reload` | Reload PgBouncer |
| GET | `/api/capacity` | Connection budget per target Postgres |

## Security

**The API has no authentication and CORS defaults to `*`.** Put it behind a
reverse proxy with auth and TLS before exposing it beyond localhost, and
restrict `CORS_ORIGINS`. The proxy must cover `/` as well as `/api`, or the UI
will be reachable unauthenticated.

Passwords are hashed to PgBouncer-compatible SCRAM-SHA-256 (or md5) before they
touch disk — plaintext is never written.

The files are the state, and writes assume a **single writer**. Do not run two
manager instances against one shared config volume.

## License

MIT
