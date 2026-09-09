# Secure Docker Compose deployment

`../docker-compose.yml` is the minimal stack that demonstrates the management
loop. This one is the same loop with the defaults you would actually deploy.

## What is different

| | Minimal example | This stack |
|---|---|---|
| PgBouncer client auth | `trust` | `scram-sha-256` |
| Pooler → Postgres | plaintext | `server_tls_sslmode = require` |
| Manager port | published on `:3000` | not published; reachable only through an authenticating proxy |
| Manager auth | none | basic auth + security headers at the proxy |
| Containers | default | unprivileged, read-only rootfs, all capabilities dropped, `no-new-privileges` |
| Admin console | TCP | shared unix socket, authenticated by peer uid |
| Postgres password | `trust` | Docker secret |
| Tenants | added one API call at a time | declared in `tenants.yaml` |

## The admin-console detail worth knowing

PgBouncer grants admin access over a unix socket based on the connecting
process's uid. PgBouncer and the manager both run as uid 1100 and share a
socket volume, so `RELOAD` works with **no admin password existing anywhere**.

The alternative — reaching the admin console over TCP — needs an admin user in
`userlist.txt` and a password in the manager's environment, which is a
credential you then have to store, rotate and protect. Compare with
[the Kubernetes deployment](../../docs/deployment/kubernetes.md), where the
operator's reload sidecar signals PgBouncer directly for the same reason.

The other common approach, giving the manager the Docker socket so it can
`docker kill --signal=HUP`, is worse still: the Docker socket is root on the
host. `RELOAD_CONTAINERS` is left empty here on purpose.

## Setup

```bash
cd examples/secure

cp .env.example .env
printf 'a-real-password\n' > secrets/postgres_password

# Generate the proxy's basic-auth hash and put it in .env
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'your-password'

docker compose up -d --build
```

The manager UI is then at `http://localhost:8080`, behind basic auth. It is
still HTTP — put a real certificate on the proxy before exposing it beyond
localhost.

## Declaring tenants

Edit `tenants.yaml`, put the passwords in `.env`, then:

```bash
docker compose run --rm cli apply -f /work/tenants.yaml --dry-run
docker compose run --rm cli apply -f /work/tenants.yaml
```

`apply` creates what is missing, patches what differs, and does nothing when
the file already matches — so re-running it does not churn credentials or
reload PgBouncer needlessly. Add `--prune` to delete tenants the file no longer
mentions.

Passwords are sent on create only. Re-sending one would re-hash it with a fresh
salt on every run, rewriting `userlist.txt` and triggering a reload each time;
use `--rotate-credentials` when you actually mean to rotate.

`tenants.yaml` uses the same schema as the Kubernetes `PgBouncerDatabase`
resource. Moving this deployment to a cluster is a translation, not a redesign.

## Before you call it production

- **Give the proxy a real certificate.** Caddy will provision one automatically
  if you give it a domain instead of `:8080` and remove `auto_https off`.
- **Verify the upstream certificate.** `server_tls_sslmode = require` encrypts
  but does not authenticate the server; use `verify-full` with a
  `server_tls_ca_file` once you have the CA in place.
- **Set `CAPACITY_LIMITS`** to each target's real `max_connections`. Pool sizes
  sum against it, and without the limit `/api/capacity` reports `unknown`
  rather than guessing.
- **Back up the config volume**, or keep `tenants.yaml` in git as the source of
  truth and rebuild from it. There is no database behind this tool; the files
  are the state.
- **One manager per config volume.** Writes are atomic but assume a single
  writer; two managers on a shared volume will race.
