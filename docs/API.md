# API Documentation

## Base URL

```
http://localhost:3000
```

## Tenants

### List All Tenants

```http
GET /tenants HTTP/1.1
```

```json
[
  {
    "id": "tenant1",
    "host": "db.example.com",
    "port": 5432,
    "db_name": "postgres",
    "user": "postgres",
    "pool_size": 15
  }
]
```

### Add Tenant

```http
POST /tenants HTTP/1.1
Content-Type: application/json

{
  "id": "tenant1",
  "host": "db.example.com",
  "port": 5432,
  "db_name": "postgres",
  "user": "postgres",
  "password": "secret123",
  "pool_size": 15
}
```

### Get Tenant

```http
GET /tenants/tenant1 HTTP/1.1
```

```json
{
  "id": "tenant1",
  "host": "db.example.com",
  "port": 5432,
  "db_name": "postgres",
  "user": "postgres",
  "pool_size": 15
}
```

### Update Tenant

```http
PATCH /tenants/tenant1 HTTP/1.1
Content-Type: application/json

{
  "pool_size": 20,
  "password": "newsecret"
}
```

### Delete Tenant

```http
DELETE /tenants/tenant1 HTTP/1.1
```

```json
{
  "message": "Tenant deleted"
}
```

## Pools

### List Pool Status

```http
GET /pools/status HTTP/1.1
```

```json
{
  "pools": [
    {
      "database": "tenant1",
      "user": "postgres",
      "pool_mode": "transaction",
      "active": 10,
      "waiting": 0,
      "idle": 5,
      "max_wait": 0
    }
  ]
}
```

### List Connection Statistics

```http
GET /pools/stats HTTP/1.1
```

```json
{
  "stats": [
    {
      "database": "tenant1",
      "user": "postgres",
      "type": "client",
      "state": "active",
      "addr": "10.0.0.1",
      "port": 5432,
      "local_addr": "10.0.0.2",
      "local_port": 6432,
      "create_time": 1234567890
    }
  ]
}
```

### Reload PgBouncer

```http
POST /pools/reload HTTP/1.1
```

```json
{
  "status": "success",
  "message": "PgBouncer reloaded"
}
```
