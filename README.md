# PgBouncer Manager

PgBouncer is configured with two flat files — `databases.ini` (which tenant
routes where) and `userlist.txt` (who can connect) — and a small admin console
you talk to over the Postgres wire protocol. Editing those files by hand across
many tenants is tedious and easy to get wrong, and PgBouncer won't tell you when
you've corrupted them.

**This project is a typed, safe editor for those two files, plus a live view of
the admin console** — exposed as a FastAPI service, a CLI, and a React UI.

API docs (Swagger): `http://localhost:3000/docs` · Project docs: `https://adams-okode.github.io/pgbouncer-manager/`

## The mental model

There is no database behind this tool. **PgBouncer's config files *are* the
state.** Every request reads the current files, applies a change, and writes
them back:

```
            ┌──────────────┐   read/write     ┌────────────────┐
  API / CLI │ PgBouncer    │ ───────────────▶ │ databases.ini  │
  ─────────▶│ Manager      │                  │ userlist.txt   │
            │ (service     │ ── psql ───────▶  └────────────────┘
            │  layer)      │   SHOW POOLS /          ▲ PgBouncer reads these
            └──────────────┘   STATS / RELOAD ───────┘
```

That single decision explains most of the design:

- **There's nothing to migrate or back up except the files themselves.** The
  files are the source of truth; the tool is stateless.
- **Changes must be reload-safe.** A half-written `databases.ini` is a broken
  PgBouncer, so writes are atomic (temp file → `fsync` → `os.replace`). A crash
  mid-write leaves the old, valid file in place.
- **The manager has to run where the files are.** See *Deployment model* below.

## What it actually does

- **Tenant CRUD** — add / list / update / delete entries in `databases.ini`.
  Updates are partial (`PATCH` only what you pass; pool size without touching
  the password, or vice versa).
- **Credential handling done right** — passwords are never stored in plaintext.
  They're hashed into a format PgBouncer understands before being written to
  `userlist.txt`: **SCRAM-SHA-256** by default (salted, iterated), or `md5`.
  "Rotating" a credential is just `PATCH /tenants/{id}` with a new password.
- **Live pool monitoring** — `SHOW POOLS` / `SHOW STATS` from the admin console,
  parsed by *column name* (not fragile positional splitting), so PgBouncer
  version changes that add columns don't break it.
- **Reload without downtime** — `SIGHUP` to PgBouncer container(s), or `RELOAD`
  over the admin console when no containers are configured.

### Why hashing, not encryption

PgBouncer reads `userlist.txt` itself, so credentials can't be encrypted at rest
and still be usable — they have to be in a format PgBouncer accepts. Storing a
SCRAM-SHA-256 verifier means the plaintext password exists only long enough to
compute the hash and is never written to disk. (Earlier docs claimed AES-256-GCM
encryption; that was never real and has been removed.)

## Quick start

```bash
# Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export CONFIG_DIR=/path/to/pgbouncer/config   # where databases.ini lives
uvicorn app.main:app --reload --port 3000

# UI (separate terminal) — dev server proxies /api → :3000
cd ui && npm install && npm run dev

# Add a tenant (its password is hashed before it touches userlist.txt)
curl -X POST http://localhost:3000/tenants \
  -H "Content-Type: application/json" \
  -d '{"id":"tenant1","host":"db.example.com","user":"svc","password":"secret123","pool_size":15}'

curl http://localhost:3000/pools/status
```

## Configuration

Everything is environment variables (or a `.env` file). The ones you'll actually
touch:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CONFIG_DIR` | `/etc/pgbouncer` | Directory holding `databases.ini` + `userlist.txt` |
| `AUTH_SCHEME` | `scram-sha-256` | Credential hashing: `scram-sha-256`, `md5`, or `plain` (testing only) |
| `ADMIN_HOST` / `ADMIN_PORT` | `localhost` / `6432` | PgBouncer admin console for SHOW/RELOAD |
| `RELOAD_CONTAINERS` | `[]` | JSON list of Docker containers to `SIGHUP`; empty ⇒ reload via admin console |
| `CORS_ORIGINS` | `["*"]` | Allowed browser origins for the API |

## API

| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET` | `/` | Health check |
| `GET` | `/tenants` | List tenants (array) |
| `POST` | `/tenants` | Add tenant — `201`, or `409` if it exists, `422` on a bad id |
| `GET` | `/tenants/{id}` | One tenant, or `404` |
| `PATCH` | `/tenants/{id}` | Partial update; omit `password` to keep the existing one |
| `DELETE` | `/tenants/{id}` | Removes the tenant; drops its user only if no other tenant uses it |
| `GET` | `/pools/status` | `SHOW POOLS` (active / waiting / idle / max_wait) |
| `GET` | `/pools/stats` | `SHOW STATS` (raw columns) |
| `POST` | `/pools/reload` | `SIGHUP` containers or admin `RELOAD` |

## CLI

The CLI is a thin HTTP client of the API — no separate config, just point it at
a running server (`--api-url` or `PGBM_API_URL`, default `http://localhost:3000`).

```bash
python -m cli.tenant tenant-add --id=tenant1 --host=db.example.com --user=svc --password=secret123
python -m cli.tenant tenant-update --id=tenant1 --pool-size=20   # partial: only pool size changes
python -m cli.tenant tenant-list
python -m cli.tenant pools-list
python -m cli.tenant reload
```

## Deployment model

Because the files are the source of truth, **the manager must be able to write
the same `databases.ini`/`userlist.txt` that PgBouncer reads.** In practice:

- **Co-located (recommended):** run the manager next to PgBouncer — same host or
  a sidecar in the same pod — sharing the config directory. Reload locally via
  `SIGHUP`.
- **Remote PgBouncer:** mount a shared config volume at `CONFIG_DIR` on both
  sides and leave `RELOAD_CONTAINERS` empty so reload goes over the admin
  console. Note the admin console must then be network-reachable and secured.
  Pointing the manager at a remote PgBouncer *without* sharing the files is a
  silent no-op: writes land on the manager's local disk and never reach the
  bouncer.

```bash
docker build -t pgbouncer-manager .
docker run -p 3000:3000 \
  -e CONFIG_DIR=/app/config \
  -v /path/to/pgbouncer/config:/app/config \   # read-write: the manager edits these files
  pgbouncer-manager
```

## Limitations & non-goals

- **No authentication on the API**, and CORS defaults to `*`. Put it behind a
  reverse proxy with auth/TLS before exposing it beyond localhost, and restrict
  `CORS_ORIGINS`.
- **Single-writer assumption.** The files are the state; concurrent writers (two
  manager instances on a shared volume) can race. Run one writer.
- **It manages tenants and pool sizing, not PgBouncer's global config.**
  Top-level settings (`pool_mode` defaults, `server_lifetime`, TLS, etc.) still
  live in `pgbouncer.ini`.

## Development

```bash
pytest          # unit + API tests (atomic IO, hashing, tenant CRUD, pool parsing)
ruff check .    # lint
mypy app cli    # type check
cd ui && npm run build   # type-check + build the SPA
```

CI runs the same checks; docs deploy to GitHub Pages on `docs/**` changes,
images publish to Docker Hub on `main`, and tags cut GitHub releases.

## License

MIT
