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
