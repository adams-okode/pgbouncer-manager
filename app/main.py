"""PgBouncer Manager - FastAPI backend for managing PgBouncer tenants."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import tenants, pools

app = FastAPI(title="PgBouncer Manager", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tenants.router)
app.include_router(pools.router)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"service": "pgbouncer-manager", "status": "ok"}


@app.on_event("startup")
async def startup_event():
    """Startup logic."""
    config_dir = os.environ.get("CONFIG_DIR", "/path/to/pgbouncer/config")
    os.environ["CONFIG_DIR"] = config_dir


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=3000, reload=True)
