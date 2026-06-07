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
  [--pool-size=<size>]
```

**Options:**
- `--id` (required): Unique tenant identifier
- `--host` (required): Database host
- `--user`: Database user (default: `postgres`)
- `--password` (required): Database password
- `--pool-size`: Pool size (default: `15`)

### tenant-list

List all configured tenants.

```bash
python -m cli.tenant tenant-list
```

### tenant-update

Update tenant settings.

```bash
python -m cli.tenant tenant-update \
  --id=<id> \
  [--pool-size=<size>] \
  [--password=<password>]
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

### reload

Reload PgBouncer configuration.

```bash
python -m cli.tenant reload
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CONFIG_DIR` | Path to PgBouncer config directory |
| `DOCKER_MODE` | Set to `false` for bare metal (default: `true`) |
| `PGBOUNCER_HOST` | PgBouncer host for direct reload (default: `localhost`) |
| `PGBOUNCER_PORT` | PgBouncer admin port (default: `6543`) |

## Shell Completion

### Bash

```bash
python -m cli.tenant --completion bash > /etc/bash_completion.d/pgbouncer-manager
```

### Zsh

```bash
python -m cli.tenant --completion zsh > /usr/share/zsh/site-functions/_pgbouncer-manager
```
