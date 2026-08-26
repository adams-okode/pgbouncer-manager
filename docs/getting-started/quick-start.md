# Quick Start

## 1. Start Backend

```bash
export CONFIG_DIR=/path/to/pgbouncer/config
uvicorn app.main:app --reload --port 3000
```

## 2. Add a Tenant

```bash
curl -X POST http://localhost:3000/api/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "id": "tenant1",
    "host": "db.example.com",
    "password": "secret123",
    "pool_size": 15
  }'
```

## 3. Check Pools

```bash
curl http://localhost:3000/api/pools/status
```

## 4. Check Capacity

```bash
curl http://localhost:3000/api/capacity
```

Pool sizes across tenants pointing at the same Postgres **add up**, so this
reports the total server connections your config commits per target. Set
`CAPACITY_LIMITS` to get a verdict instead of raw totals:

```bash
export CAPACITY_LIMITS='{"db.example.com:5432": 200}'
```

## 5. Load UI

In development, run `npm run dev` in `ui/` and open http://localhost:5173 — the
Vite dev server proxies `/api` through to the backend on port 3000.

In a built image the UI is bundled into the service itself and served at
http://localhost:3000, alongside the API under `/api`.
