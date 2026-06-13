# CLI Documentation

## Installation

```bash
cd /path/to/pgbouncer-manager
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Commands

### tenant-add

Add a new tenant.

```bash
python -m cli.tenant tenant-add \
  --id=<id> \
  --host=<host> \
  --user=<user> \
  --password=<password> \
  [--port=<port>] [--db-name=<name>] [--pool-size=<size>] [--pool-mode=<mode>]
```

**Options:**
- `--id` (required): Unique tenant identifier
- `--host` (required): Database host
- `--port`: Database port (default: `5432`)
- `--db-name`: Database name (default: `postgres`)
- `--user`: Database user (default: `postgres`)
- `--password` (required): Database password
- `--pool-size`: Pool size (default: `15`)
- `--pool-mode`: Optional pool mode (`session`, `transaction`, `statement`)

### tenant-list

List all configured tenants.

```bash
python -m cli.tenant tenant-list
```

### tenant-get

Show one tenant.

```bash
python -m cli.tenant tenant-get --id=<id>
```

### tenant-update

Partially update a tenant (only the flags you pass are changed).

```bash
python -m cli.tenant tenant-update \
  --id=<id> \
  [--host=<host>] [--port=<port>] [--db-name=<name>] \
  [--user=<user>] [--password=<password>] \
  [--pool-size=<size>] [--pool-mode=<mode>]
```

### tenant-remove

Remove a tenant.

```bash
python -m cli.tenant tenant-remove --id=<id>
```

### pools-list

List all pool statistics.

```bash
python -m cli.tenant pools-list
```

### stats-list

List connection statistics.

```bash
python -m cli.tenant stats-list
```

### reload

Reload PgBouncer configuration.

```bash
python -m cli.tenant reload
```

## Configuration

The CLI is a thin HTTP client of the running API. Point it at the API with
either the `--api-url` flag or the `PGBM_API_URL` environment variable.

| Variable | Description | Default |
|----------|-------------|---------|
| `PGBM_API_URL` | Base URL of the PgBouncer Manager API | `http://localhost:3000` |

```bash
# Example: target a remote API
python -m cli.tenant --api-url=https://pgbm.example.com tenant-list
# or
export PGBM_API_URL=https://pgbm.example.com
python -m cli.tenant tenant-list
```

