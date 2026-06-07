# Security

## Encrypted Credentials

Credentials are encrypted using AES-256-GCM. Store the encryption key securely:

```bash
openssl rand -base64 32
```

## TLS for PgBouncer

Your PgBouncer setup should have:

```ini
server_tls_sslmode = require
```

## API Security

- Use JWT authentication in production
- Enable rate limiting
- Terminate SSL at reverse proxy (Nginx/Traefik)

## File Permissions

```bash
chmod 600 .env.encryption
chmod 700 /etc/pgbouncer/config
```
