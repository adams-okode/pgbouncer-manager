# API Reference

## Base URL

```
http://localhost:3000/api
```

Every endpoint below is namespaced under `/api`. The root path `/` is reserved
for the bundled web UI (see `SERVE_UI`), so anything not matched by a route here
falls through to the SPA.

The API ships with **no authentication**. Put it behind an authenticating proxy
before exposing the port.

## Health

### GET /api/health

```bash
curl http://localhost:3000/api/health
```

```json
{ "service": "pgbouncer-manager", "status": "ok" }
```

## Tenants

### GET /api/tenants

List all tenants.

```bash
curl http://localhost:3000/api/tenants
```

### POST /api/tenants

Add a new tenant.

```bash
curl -X POST http://localhost:3000/api/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "id": "tenant1",
    "host": "db.example.com",
    "password": "secret123"
  }'
```

### GET /api/tenants/{id}

Get tenant details.

```bash
curl http://localhost:3000/api/tenants/tenant1
```

### PATCH /api/tenants/{id}

Update tenant settings.

```bash
curl -X PATCH http://localhost:3000/api/tenants/tenant1 \
  -H "Content-Type: application/json" \
  -d '{"pool_size": 20}'
```

### DELETE /api/tenants/{id}

Remove a tenant.

```bash
curl -X DELETE http://localhost:3000/api/tenants/tenant1
```

## Pools

### GET /api/pools/status

List pool statistics.

```bash
curl http://localhost:3000/api/pools/status
```

### GET /api/pools/stats

List connection statistics.

```bash
curl http://localhost:3000/api/pools/stats
```

### POST /api/pools/reload

Reload PgBouncer configuration.

```bash
curl -X POST http://localhost:3000/api/pools/reload
```

## Capacity

### GET /api/capacity

How many server connections are committed to each target Postgres, grouped by
`host:port`.

Every `databases.ini` entry is its own PgBouncer pool — a pool is keyed on the
entry name plus the forced user, not on the target database — so `pool_size`
values across entries **add up** rather than overlap. Ten tenants pointing at
the same Postgres with `pool_size=15` commit 150 server connections, not 15.

```bash
curl http://localhost:3000/api/capacity
```

```json
{
  "targets": [
    {
      "host": "db.example.com",
      "port": 5432,
      "tenants": ["tenant1", "tenant2"],
      "declared_total": 30,
      "reserve_total": 0,
      "worst_case_total": 30,
      "current_connections": null,
      "max_connections": 100,
      "headroom": 67,
      "utilization": 0.3093,
      "status": "ok",
      "source": "databases.ini",
      "unbounded_pools": []
    }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `declared_total` | Sum of `pool_size` across every entry for this target |
| `reserve_total` | Sum of `reserve_pool_size`, which PgBouncer may open on top of `pool_size` |
| `worst_case_total` | `declared_total + reserve_total` — the ceiling this config can reach |
| `max_connections` | The target's ceiling from `CAPACITY_LIMITS`, or `null` if unknown |
| `headroom` | `max_connections − superuser reserve − worst_case_total` |
| `utilization` | `worst_case_total` as a ratio of usable connections (`0`–`1`), not a percentage |
| `unbounded_pools` | Entries with no forced `user=`; PgBouncer opens one pool *per connecting user*, so the real total can exceed `worst_case_total` |

`status` is one of:

| Status | Meaning |
|--------|---------|
| `ok` | Worst case fits with room to spare |
| `tight` | Worst case is above `CAPACITY_TIGHT_RATIO` (default `0.8`) of usable connections |
| `oversubscribed` | Worst case exceeds what the target can serve |
| `unknown` | No `CAPACITY_LIMITS` entry for this target — the totals are still reported, but no verdict is given |

Pool sizes are read from the PgBouncer admin console when it is reachable, and
fall back to `databases.ini` when it is not; `source` says which was used.

### Configuring it

`CAPACITY_LIMITS` is a JSON map of `"host:port"` to that server's
`max_connections`. Targets absent from the map report `unknown` rather than a
guessed verdict.

```bash
export CAPACITY_LIMITS='{"db.example.com:5432": 200}'
```

Related knobs: `SUPERUSER_RESERVED_CONNECTIONS` (default `3`, subtracted from the
limit because Postgres holds those back), `ASSUMED_POOL_SIZE` (default `20`,
used for entries that omit `pool_size`, matching PgBouncer's own
`default_pool_size`), and `CAPACITY_TIGHT_RATIO` (default `0.8`).
