# Docker Deployment

## Basic

```bash
docker build -t pgbouncer-manager .
docker run -p 3000:3000 \
  -e CONFIG_DIR=/app/config \
  -v /path/to/pgbouncer/config:/app/config:ro \
  pgbouncer-manager
```

## Docker Compose

```yaml
version: '3.8'
services:
  pgbouncer-manager:
    image: adamsokode/pgbouncer-manager:latest
    container_name: pgbouncer-manager
    ports:
      - "3000:3000"
    environment:
      - CONFIG_DIR=/app/config
    volumes:
      - ./pgbouncer/config:/app/config:ro
    restart: unless-stopped
```

## Hardened Compose stack

`examples/secure/` is a production-shaped version of the stack above. The
differences are the ones that matter:

| | `examples/docker-compose.yml` | `examples/secure/` |
|---|---|---|
| PgBouncer client auth | `trust` | `scram-sha-256` |
| Pooler → Postgres | plaintext | `server_tls_sslmode = require` |
| Manager port | published on `:3000` | not published; behind an authenticating proxy |
| Containers | default | unprivileged, read-only rootfs, all capabilities dropped |
| Admin console | TCP | shared unix socket, authenticated by peer uid |
| Tenants | one API call at a time | declared in `tenants.yaml` |

```bash
cd examples/secure
cp .env.example .env
printf 'a-real-password\n' > secrets/postgres_password
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'your-password'  # -> .env
docker compose up -d --build
```

See [`examples/secure/README.md`](https://github.com/adams-okode/pgbouncer-manager/tree/main/examples/secure)
for the full walkthrough.

### The reload credential problem

Reloading PgBouncer needs either a signal or an admin-console connection, and
both have a security cost if you do them the obvious way:

- Giving the manager the **Docker socket** so it can `docker kill --signal=HUP`
  hands it root on the host. `RELOAD_CONTAINERS` is left empty in the hardened
  stack for this reason.
- Reaching the **admin console over TCP** needs an admin user in `userlist.txt`
  and a password in the manager's environment — a credential you then have to
  store, rotate and protect.

The hardened stack does neither. PgBouncer grants admin access over a **unix
socket** based on the connecting process's uid, so PgBouncer and the manager
run as the same uid and share a socket volume. `RELOAD` then works with no
admin password existing anywhere. The Kubernetes deployment solves the same
problem the same way, with a sidecar that signals the process directly.

## Declarative tenants

Once you have more than a handful, manage them from a file rather than one API
call at a time:

```bash
docker compose run --rm cli apply -f /work/tenants.yaml --dry-run
docker compose run --rm cli apply -f /work/tenants.yaml
```

See the [CLI reference](../cli.md#apply) — and note that the file uses the same
schema as the Kubernetes `PgBouncerDatabase` resource.
