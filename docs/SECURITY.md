# Security Guide

## Encrypted Credentials

### How Encryption Works

Credentials (database passwords) should be encrypted using AES-256-GCM before storing.

```
Encryption: AES-256-GCM (authenticated encryption)
Key: 32-byte random key (base64 encoded)
Nonce: 12-byte random nonce per encryption
Tag: 16-byte authentication tag
```

### Generating an Encryption Key

```bash
# Generate a secure 32-byte key
openssl rand -base64 32
```

### Environment Variable

```bash
export ENCRYPTION_KEY="your-32-byte-base64-key-here"
```

### Storing the Key Securely

| Environment | Recommended Storage |
|-------------|---------------------|
| Docker Compose | Docker secrets |
| Kubernetes | Kubernetes Secrets |
| Bare Metal | Environment file with 0600 permissions |

## TLS for PgBouncer Connections

Your existing PgBouncer setup already has TLS enabled:

```ini
server_tls_sslmode = require
```

## API Security

### Authentication (Production)

Add JWT authentication middleware using `python-jose`:

```python
# Add to app/main.py
from jose import jwt, JWTError

def verify_token(token: str):
    # Verify JWT token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
```

### Rate Limiting

```python
# Add to app/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

### HTTPS Only

Use a reverse proxy (Nginx, Traefik) to handle SSL termination.

### CORS Configuration

```python
# Add to app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

## File Permissions

```bash
# Encryption key file
chmod 600 .env.encryption
chown pgbouncer:pgbouncer .env.encryption

# Config directory
chmod 700 /etc/pgbouncer/config
chmod 640 /etc/pgbouncer/config/*
```

## Audit Logging

### Logging Configuration

```python
# Add to app/main.py
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### Audit Events

| Event | Description |
|-------|-------------|
| `tenant.add` | New tenant added |
| `tenant.update` | Tenant settings modified |
| `tenant.remove` | Tenant deleted |
| `credentials.rotate` | Credentials rotated |
| `credentials.update` | Credentials manually updated |
| `config.reload` | PgBouncer configuration reloaded |
