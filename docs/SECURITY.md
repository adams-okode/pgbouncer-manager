# Security Guide

## Credential Storage

PgBouncer authenticates clients against `userlist.txt`, which it reads directly.
Credentials must therefore be stored in a PgBouncer-readable format — they
cannot be encrypted at rest and still be usable. This project stores **hashed**
credentials and never plaintext.

### Supported schemes (`AUTH_SCHEME`)

| Scheme | Format | Notes |
|--------|--------|-------|
| `scram-sha-256` (default) | `SCRAM-SHA-256$<iterations>:<salt>$<StoredKey>:<ServerKey>` | Salted + iterated (PBKDF2-HMAC-SHA256). Recommended. |
| `md5` | `md5` + `md5(password + username)` | Legacy, still widely supported. |
| `plain` | the password verbatim | Local testing only. Never use in production. |

### How SCRAM-SHA-256 hashing works

```
SaltedPassword = PBKDF2-HMAC-SHA256(password, salt, iterations)
ClientKey      = HMAC(SaltedPassword, "Client Key")
StoredKey      = SHA256(ClientKey)
ServerKey      = HMAC(SaltedPassword, "Server Key")
verifier       = SCRAM-SHA-256$iterations:b64(salt)$b64(StoredKey):b64(ServerKey)
```

A fresh random 16-byte salt is generated for every credential. Iterations
default to `4096` and are configurable via `SCRAM_ITERATIONS`.

> **Correction:** previous versions of this guide described AES-256-GCM
> encryption of credentials and a required `ENCRYPTION_KEY`. That feature was
> never implemented and the claim was removed. The `cryptography` dependency
> has also been dropped.

## TLS for PgBouncer Connections

```ini
server_tls_sslmode = require
```

## API Security

The API has no built-in authentication. For anything beyond local use:

### Reverse proxy + TLS

Terminate TLS at Nginx/Traefik and forward to the app over localhost.

### Authentication and rate limiting

Add authentication (JWT, mTLS, or proxy-level auth) and rate limiting at the
edge. These are deployment concerns and are intentionally not bundled.

### CORS Configuration

Set `CORS_ORIGINS` to your UI origin instead of the permissive `*` default:

```bash
export CORS_ORIGINS='["https://yourdomain.com"]'
```

## File Permissions

```bash
chmod 700 "$CONFIG_DIR"
chmod 640 "$CONFIG_DIR"/userlist.txt "$CONFIG_DIR"/databases.ini
```

## Audit Logging

Operations emit structured log lines via the `pgbouncer_manager.audit` logger.

| Event | Description |
|-------|-------------|
| `tenant.add` | New tenant added |
| `tenant.update` | Tenant settings or credential modified |
| `tenant.remove` | Tenant deleted |
| `config.reload` | PgBouncer configuration reloaded |
