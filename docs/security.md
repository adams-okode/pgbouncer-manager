# Security

## Credential Storage

PgBouncer reads credentials from `userlist.txt` itself, so passwords cannot be
encrypted at rest in a way PgBouncer could still use — they must be stored in a
format PgBouncer understands. This project therefore stores **hashed**
credentials, never plaintext:

- **SCRAM-SHA-256** (default) — salted, iterated (PBKDF2) verifier, the same
  format PostgreSQL 10+ uses. Configure with `AUTH_SCHEME=scram-sha-256`.
- **md5** — legacy `md5(password + username)` digest. `AUTH_SCHEME=md5`.
- **plain** — stores the password verbatim. Only for local testing; never use
  in production. `AUTH_SCHEME=plain`.

The plaintext password is only ever received over the API/CLI to compute the
hash; it is never written to disk.

> Note: this project does **not** implement AES-256-GCM encryption. Earlier
> drafts of these docs claimed it did — that was inaccurate and has been
> corrected.

## TLS for PgBouncer

There are two legs, and they are configured separately.

**Pooler to Postgres:**

```ini
server_tls_sslmode = require      ; encrypts, but does not authenticate the server
server_tls_sslmode = verify-full  ; encrypts and verifies; needs server_tls_ca_file
```

**Client to pooler** — often forgotten, and the one that carries the SCRAM
exchange:

```ini
client_tls_sslmode = require
client_tls_cert_file = /etc/pgbouncer/tls/tls.crt
client_tls_key_file = /etc/pgbouncer/tls/tls.key
```

The Kubernetes operator renders the client-side block from `spec.tls` and warns
on the pooler's status when either leg is unencrypted.

## API Security

The API ships without authentication. Before exposing it beyond localhost:

- Put it behind a reverse proxy (Nginx/Traefik) that terminates TLS.
- Add authentication (e.g. JWT or mTLS) and rate limiting at the proxy or app.
- Restrict `CORS_ORIGINS` to your UI origin instead of the `*` default.

## The bundled web UI

When the UI is built into the image it is served at `/` (`SERVE_UI=true`, the
default). That UI is a thin client over the same unauthenticated API, so
publishing the port publishes tenant management — anyone who can reach it can
add, edit, or delete tenants without a credential.

- Keep the port on a private network, or front it with an authenticating proxy.
  The proxy must cover `/` as well as `/api`; protecting only `/api` still
  serves the UI to anonymous visitors.
- Set `SERVE_UI=false` to run API-only where the UI has no business being
  reachable — for example a cluster-internal deployment driven purely by the CLI.

The service logs a warning at startup whenever it mounts the UI, as a reminder
that the surface is unauthenticated.

## Read-only mode

Set `READ_ONLY=true` and the API refuses every config-mutating call with a 409,
while reads keep working. Use it wherever something else owns `databases.ini`
and `userlist.txt`.

The Kubernetes deployment sets it automatically. There the custom resources are
the source of truth, so an edit made through the API would be reverted on the
operator's next reconcile — failing loudly beats accepting a change that will
not survive. The bundled UI reads the flag from `/api/health` and hides the
controls rather than offering edits that will 409.

## Kubernetes

The [operator](deployment/kubernetes.md) changes where credentials live but not
how they are stored: passwords come from Secrets, are hashed into
SCRAM-SHA-256 verifiers by the same code, and only the hash reaches the
rendered config.

- **Passwords must come from a Secret.** The `PgBouncerDatabase` CRD accepts
  only `password.secretKeyRef`, never an inline value. A password in a custom
  resource is not covered by the encryption-at-rest defaults or the RBAC most
  clusters put around secret reads.
- **The operator cannot enumerate Secrets.** Its RBAC grants `get` but not
  `list` or `watch`, so a leaked operator token can read only the Secrets
  already named in a `PgBouncerDatabase`. The cost is that a rotated password
  is picked up on the resync interval rather than instantly.
- **Reserved config options are rejected.** `spec.settings` cannot set
  `auth_file`, `auth_type`, `auth_query`, `admin_users`, `listen_*` or
  `client_tls_*`. Allowing it would let whoever can edit a pooler downgrade
  authentication to `trust` for every database behind it.
- **Config values are validated, not interpolated.** A `databases.ini` value
  containing whitespace, or a `pgbouncer.ini` value containing a newline, is
  rejected rather than written — otherwise a hostname of
  `db1\nauth_type = trust` injects a directive.
- **Pods are unprivileged.** Non-root, read-only root filesystem, all
  capabilities dropped, no privilege escalation, `seccompProfile:
  RuntimeDefault`, and no service-account token on the pooler pod.
- **The config Secret is mounted `0440`**, not world-readable. A SCRAM verifier
  is not a plaintext password, but it is offline-crackable against a weak one.

Two things are not on by default and should be:

- `pooler.tls.enabled` — otherwise the client-to-pooler leg, including the
  SCRAM exchange, crosses the network in the clear.
- `networkPolicy.enabled` — a pooler holds credentials for every database
  behind it, so anything that can open a socket to it is one weak client
  password away from your data.

## File Permissions

```bash
chmod 700 "$CONFIG_DIR"
chmod 640 "$CONFIG_DIR"/userlist.txt "$CONFIG_DIR"/databases.ini
```

## Audit Logging

Tenant and reload operations emit structured audit log lines under the
`pgbouncer_manager.audit` logger:

| Event | Description |
|-------|-------------|
| `tenant.add` | New tenant added |
| `tenant.update` | Tenant settings or credential modified |
| `tenant.remove` | Tenant deleted |
| `config.reload` | PgBouncer configuration reloaded |
