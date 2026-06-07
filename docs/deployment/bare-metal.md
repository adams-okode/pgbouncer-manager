# Bare Metal Deployment

## Systemd Service

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

## Manual

```bash
python -m venv /opt/pgbouncer-manager/venv
source /opt/pgbouncer-manager/venv/bin/activate
pip install -r requirements.txt

# Create service user
useradd -r -s /bin/false pgbouncer

# Start
cd /opt/pgbouncer-manager
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 3000
```
