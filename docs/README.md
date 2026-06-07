# PgBouncer Manager

Manage PgBouncer tenants, pool sizes, and credentials with a REST API, CLI, and web interface.

## Features

- **REST API** - Full CRUD for tenant management
- **CLI** - Scriptable admin operations
- **Web UI** - Visual tenant and pool monitoring
- **Docker Integration** - Auto-reload PgBouncer configs via SIGHUP
- **Encrypted Credentials** - AES-256-GCM encryption for database passwords

## Architecture

```
pgbouncer-manager/
├── cmd/
│   ├── server/      # Go API server (Fiber)
│   └── cli/         # CLI tool (Cobra)
├── internal/
│   ├── api/         # HTTP routes and handlers
│   ├── config/      # INI parser/writer
│   ├── pgbouncer/   # PgBouncer operations (reload, queries)
│   ├── models/      # Data structures
│   └── storage/     # Encrypted credential storage
├── ui/              # React SPA (Vite)
└── docs/            # Documentation
```

## Installation

### Prerequisites

- Go 1.23+
- Node.js 23+
- Docker (for PgBouncer integration)

### Build and Run

```bash
# Build the backend server
cd cmd/server
go build -o ../../bin/server .

# Build the React UI
cd ../../ui
npm install
npm run build

# Run the server
../../bin/server
```

## Configuration

```bash
# Set environment variables
export CONFIG_DIR=/path/to/pgbouncer/config
export ENCRYPTION_KEY=your-32-byte-encryption-key
export PORT=3000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /tenants | Add a new tenant |
| GET | /tenants | List all tenants |
| GET | /tenants/:id | Get tenant details |
| PATCH | /tenants/:id | Update tenant |
| DELETE | /tenants/:id | Remove tenant |
| POST | /tenants/:id/rotate-credentials | Rotate tenant credentials |
| PUT | /tenants/:id/credentials | Set tenant credentials manually |
| GET | /pools | List pool statistics |
| GET | /stats | List connection statistics |
| POST | /reload | Reload PgBouncer configuration |

## CLI Commands

```bash
# Add a tenant
pgbouncer-manager tenant add \
  --id=mytenant \
  --host=db.example.com \
  --user=myuser \
  --password=mysecret \
  --pool-size=20

# List tenants
pgbouncer-manager tenant list

# Update tenant pool size
pgbouncer-manager tenant update \
  --id=mytenant \
  --pool-size=25

# Remove a tenant
pgbouncer-manager tenant remove --id=mytenant

# List pools
pgbouncer-manager pools list

# Reload PgBouncer
pgbouncer-manager reload
```

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  pgbouncer-manager:
    build: .
    ports:
      - "3000:3000"
    environment:
      - CONFIG_DIR=/app/config
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    volumes:
      - ./pgbouncer-config:/app/config
```

### Kubernetes

See `docs/DEPLOYMENT.md` for Kubernetes deployment instructions.

## Security

- Credentials are encrypted using AES-256-GCM
- Encryption key must be exactly 32 bytes
- Store key securely (environment variable, secrets manager)
- PgBouncer uses TLS by default (`server_tls_sslmode = require`)

## Contributing

1. Create a feature branch
2. Run tests: `go test ./...`
3. Lint: `golangci-lint run`
4. Submit a pull request

## License

MIT
