# API Reference

## Base URL

```
http://localhost:3000
```

## Tenants

### GET /tenants

List all tenants.

```bash
curl http://localhost:3000/tenants
```

### POST /tenants

Add a new tenant.

```bash
curl -X POST http://localhost:3000/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "id": "tenant1",
    "host": "db.example.com",
    "password": "secret123"
  }'
```

### GET /tenants/{id}

Get tenant details.

```bash
curl http://localhost:3000/tenants/tenant1
```

### PATCH /tenants/{id}

Update tenant settings.

```bash
curl -X PATCH http://localhost:3000/tenants/tenant1 \
  -H "Content-Type: application/json" \
  -d '{"pool_size": 20}'
```

### DELETE /tenants/{id}

Remove a tenant.

```bash
curl -X DELETE http://localhost:3000/tenants/tenant1
```

## Pools

### GET /pools/status

List pool statistics.

```bash
curl http://localhost:3000/pools/status
```

### GET /pools/stats

List connection statistics.

```bash
curl http://localhost:3000/pools/stats
```

### POST /pools/reload

Reload PgBouncer configuration.

```bash
curl -X POST http://localhost:3000/pools/reload
```
