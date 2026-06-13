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

Configure your PgBouncer to require TLS to upstream databases:

```ini
server_tls_sslmode = require
```

## API Security

The API ships without authentication. Before exposing it beyond localhost:

- Put it behind a reverse proxy (Nginx/Traefik) that terminates TLS.
- Add authentication (e.g. JWT or mTLS) and rate limiting at the proxy or app.
- Restrict `CORS_ORIGINS` to your UI origin instead of the `*` default.

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
