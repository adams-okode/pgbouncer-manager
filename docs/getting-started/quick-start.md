# Quick Start

## 1. Start Backend

```bash
export CONFIG_DIR=/path/to/pgbouncer/config
uvicorn app.main:app --reload --port 3000
```

## 2. Add a Tenant

```bash
curl -X POST http://localhost:3000/tenants \
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
curl http://localhost:3000/pools/status
```

## 4. Load UI

Open http://localhost:5173 in your browser.
