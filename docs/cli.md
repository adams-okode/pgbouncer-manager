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


## apply

Reconcile a declarative file instead of issuing one call per tenant. This is
the way to manage more than a handful of databases outside Kubernetes.

```bash
python -m cli.tenant apply -f tenants.yaml --dry-run
python -m cli.tenant apply -f tenants.yaml
```

```yaml
# tenants.yaml
defaults:
  host: db-primary.internal
  port: 5432
  poolSize: 20
  poolMode: transaction

databases:
  - name: acme
    dbname: acme_production
    user: acme
    password:
      env: ACME_DB_PASSWORD     # or: file: /run/secrets/acme  |  value: ...
  - name: globex
    dbname: globex_production
    user: globex
    poolSize: 40
    password:
      env: GLOBEX_DB_PASSWORD
```

`defaults` is merged into every entry below it, which is what keeps a file of
fifty tenants readable: they differ only where they actually differ.

`apply` creates what is missing, patches what differs, and does nothing when
the file already matches — so re-running it does not churn credentials or
reload PgBouncer needlessly. It reloads once at the end unless you pass
`--no-reload`.

| Flag | Effect |
|---|---|
| `-f`, `--file` | Path to the tenants file (required). |
| `--dry-run` | Print the plan; change nothing. |
| `--prune` | Delete tenants the file no longer mentions. Destructive; off by default. |
| `--rotate-credentials` | Also re-send passwords for tenants that already exist. |
| `--no-reload` | Skip the PgBouncer reload afterwards. |

### Why passwords are not re-sent by default

The API stores a **salted** SCRAM verifier and cannot report whether it matches
a given password. Re-sending one on every apply would re-hash it with a fresh
salt, rewrite `userlist.txt`, and reload PgBouncer on every single run. So
passwords go out on create, and on update only with `--rotate-credentials`.

### Same schema as Kubernetes

A `databases:` entry here and a `PgBouncerDatabase` spec have the same fields.
Both `poolSize` and `pool_size` parse. Moving a deployment from Compose to a
cluster is a translation, not a redesign — the only field that differs is where
the password comes from (`env`/`file` locally, `secretKeyRef` in a cluster).
