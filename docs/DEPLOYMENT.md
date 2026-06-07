# Deployment Guide

## Docker Compose

### Basic Deployment

```yaml
version: '3.8'
services:
  pgbouncer-manager:
    image: pgbouncer-manager:latest
    container_name: pgbouncer-manager
    ports:
      - "3000:3000"
    environment:
      - CONFIG_DIR=/app/config
    volumes:
      - ./pgbouncer/config:/app/config:ro
    restart: unless-stopped
```

### Docker Compose with Docker-in-Docker

```yaml
version: '3.8'
services:
  pgbouncer-manager:
    image: pgbouncer-manager:latest
    container_name: pgbouncer-manager
    ports:
      - "3000:3000"
    environment:
      - CONFIG_DIR=/app/config
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - ./pgbouncer/config:/app/config:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped
    depends_on:
      - pgbouncer-tx
      - pgbouncer-session
```

## Kubernetes

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer-manager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pgbouncer-manager
  template:
    metadata:
      labels:
        app: pgbouncer-manager
    spec:
      containers:
      - name: pgbouncer-manager
        image: pgbouncer-manager:latest
        ports:
        - containerPort: 3000
        env:
        - name: CONFIG_DIR
          value: "/app/config"
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: pgbouncer-config
---
apiVersion: v1
kind: Service
metadata:
  name: pgbouncer-manager
spec:
  selector:
    app: pgbouncer-manager
  ports:
  - port: 3000
    targetPort: 3000
```

## Bare Metal

### Systemd Service

```ini
[Unit]
Description=PgBouncer Manager
After=network.target

[Service]
Type=simple
User=pgbouncer
Group=pgbouncer
WorkingDirectory=/opt/pgbouncer-manager
ExecStart=/opt/pgbouncer-manager/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 3000
Environment=CONFIG_DIR=/etc/pgbouncer/config

[Install]
WantedBy=multi-user.target
```

### Init Script

```bash
#!/bin/bash
# /etc/init.d/pgbouncer-manager

DAEMON=/opt/pgbouncer-manager/venv/bin/uvicorn
DAEMON_NAME=pgbouncer-manager
DAEMON_USER=pgbouncer
PIDFILE=/var/run/$DAEMON_NAME.pid

. /lib/lsb/init-functions

case "$1" in
  start)
    log_daemon_msg "Starting $DAEMON_NAME"
    start-stop-daemon --start --quiet --pidfile $PIDFILE \
      --chuid $DAEMON_USER --background --make-pidfile \
      --exec $DAEMON -- app.main:app --host 0.0.0.0 --port 3000
    log_end_msg $?
    ;;
  stop)
    log_daemon_msg "Stopping $DAEMON_NAME"
    start-stop-daemon --stop --quiet --pidfile $PIDFILE
    log_end_msg $?
    ;;
  restart)
    $0 stop
    $0 start
    ;;
  status)
    status_of_proc -p $PIDFILE $DAEMON $DAEMON_NAME && exit 0 || exit $?
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
```

## SSL/TLS for API

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name pgbouncer-manager.example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
