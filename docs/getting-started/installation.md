# Installation

## Prerequisites

- Python 3.11+
- Node.js 23+
- Docker (optional, for PgBouncer integration)
- psql client

## Backend

```bash
cd /path/to/pgbouncer-manager
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## UI

```bash
cd ui
npm install
```

## Run

```bash
# Backend
export CONFIG_DIR=/path/to/pgbouncer/config
uvicorn app.main:app --reload --port 3000

# UI
cd ui && npm run dev
```
