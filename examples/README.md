# Example: PgBouncer + Postgres managed live

A self-contained stack that runs a real PgBouncer in front of a real Postgres,
with `pgbouncer-manager` editing PgBouncer's config files live. It demonstrates
the core idea of the project end-to-end: **the config files are the state, and
the manager is a safe editor for them.**

```
client ──▶ pgbouncer:6432 ──▶ postgres:5432
               ▲ reads /etc/pgbouncer/{databases.ini,userlist.txt}
               │
 manager:3000 ─┘ writes those files + RELOADs over the admin console
```

All three services share one config directory via the `pgbconf` named volume —
which is exactly the co-located deployment model the manager assumes.

## Run it

```bash
cd examples
docker compose up --build      # then browse http://localhost:3000/docs
```

## Run the end-to-end test

```bash
examples/test/run.sh
```

It brings the stack up and asserts the full loop:

1. `POST /tenants` adds tenant **t1** (routing to the `tenantdb` database).
2. The credential is written to `userlist.txt` as a **SCRAM-SHA-256** verifier —
   the test fails if the plaintext ever appears.
3. `POST /pools/reload` reloads PgBouncer over the admin console.
4. A client connects **through PgBouncer** (`dbname=t1`) and runs a query,
   proving PgBouncer picked up the new route.
5. `GET /pools/status` shows the live pool.

The script cleans up (`docker compose down -v`) on exit.

## Files

| Path | Purpose |
|------|---------|
| `docker-compose.yml` | The 4-service stack (init, postgres, pgbouncer, manager) |
| `pgbouncer/Dockerfile` | Minimal file-driven PgBouncer image |
| `seed/pgbouncer.ini` | Base PgBouncer config; `%include`s the manager-owned `databases.ini` |
| `seed/databases.ini`, `seed/userlist.txt` | Empty starting files seeded into the volume |
| `postgres/init.sql` | Creates the `tenantdb` database |
| `test/run.sh` | End-to-end test |

## A note on auth (important)

This example uses `auth_type = trust` in PgBouncer and `POSTGRES_HOST_AUTH_METHOD=trust`
in Postgres so the focus stays on the management loop without backend-password
plumbing. The manager **still** writes genuine SCRAM-SHA-256 verifiers, and the
test asserts that — but under `trust`, PgBouncer doesn't actually enforce them
for client logins.

To enforce credentials end-to-end you would:

- set `auth_type = scram-sha-256` in `seed/pgbouncer.ini`,
- ensure each tenant's PgBouncer password matches what the backend expects
  (e.g. via SCRAM pass-through, or `auth_user`/`auth_query` against Postgres), and
- give the manager an admin-console password if the console itself is secured.

These are deliberately out of scope for a minimal local example. **Trust auth is
for local demos only — never use it in production.**
