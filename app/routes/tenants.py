"""Tenant management API endpoints."""

import os
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/tenants", tags=["tenants"])

CONFIG_DIR = os.environ.get("CONFIG_DIR", "/root/Projects/Predicta/predicta-infra/pgbouncer/config")


class TenantCreate(BaseModel):
    id: str
    host: str
    port: int = 5432
    db_name: str = "postgres"
    user: str = "postgres"
    password: str
    pool_size: int = 15


class TenantResponse(BaseModel):
    id: str
    host: str
    port: int
    db_name: str
    user: str
    pool_size: int


def parse_databases_ini() -> dict[str, str]:
    """Parse databases.ini file."""
    databases = {}
    try:
        with open(f"{CONFIG_DIR}/databases.ini") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith((";", "#")):
                    continue
                if "=" in line:
                    tenant_id, config = line.split("=", 1)
                    databases[tenant_id.strip()] = config.strip()
    except FileNotFoundError:
        pass
    return databases


def parse_userlist_txt() -> dict[str, str]:
    """Parse userlist.txt file."""
    users = {}
    try:
        with open(f"{CONFIG_DIR}/userlist.txt") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith((";", "#")):
                    continue
                match = re.match(r'"([^"]+)"\s+"([^"]+)"', line)
                if match:
                    users[match.group(1)] = match.group(2)
    except FileNotFoundError:
        pass
    return users


def save_databases(databases: dict[str, str]) -> None:
    """Save databases.ini file."""
    lines = []
    for tenant_id, config in databases.items():
        lines.append(f"{tenant_id} = {config}")
    with open(f"{CONFIG_DIR}/databases.ini", "w") as f:
        f.write("\n".join(lines) + "\n")


def save_userlist(users: dict[str, str]) -> None:
    """Save userlist.txt file."""
    lines = ["# userlist.txt"]
    for user, pass_hash in users.items():
        lines.append(f'"{user}" "{pass_hash}"')
    with open(f"{CONFIG_DIR}/userlist.txt", "w") as f:
        f.write("\n".join(lines) + "\n")


@router.get("", response_model=list[TenantResponse])
def list_tenants():
    """List all tenants."""
    databases = parse_databases_ini()
    tenants = []
    for tenant_id, config in databases.items():
        parts = {}
        for part in config.split():
            if "=" in part:
                key, value = part.split("=", 1)
                parts[key] = value
        tenants.append(TenantResponse(
            id=tenant_id,
            host=parts.get("host", ""),
            port=int(parts.get("port", 5432)),
            db_name=parts.get("dbname", "postgres"),
            user=parts.get("user", "postgres"),
            pool_size=int(parts.get("pool_size", 15)),
        ))
    return tenants


@router.post("", response_model=TenantResponse)
def add_tenant(tenant: TenantCreate):
    """Add a new tenant."""
    databases = parse_databases_ini()
    users = parse_userlist_txt()

    # Add to databases.ini
    config = f"host={tenant.host} port={tenant.port} dbname={tenant.db_name} user={tenant.user} pool_size={tenant.pool_size}"
    databases[tenant.id] = config

    # Add to userlist.txt (password will be stored as-is for now)
    users[tenant.user] = tenant.password

    save_databases(databases)
    save_userlist(users)

    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(tenant_id: str):
    """Get tenant details."""
    databases = parse_databases_ini()
    if tenant_id not in databases:
        raise HTTPException(status_code=404, detail="Tenant not found")

    config = databases[tenant_id]
    parts = {}
    for part in config.split():
        if "=" in part:
            key, value = part.split("=", 1)
            parts[key] = value

    return TenantResponse(
        id=tenant_id,
        host=parts.get("host", ""),
        port=int(parts.get("port", 5432)),
        db_name=parts.get("dbname", "postgres"),
        user=parts.get("user", "postgres"),
        pool_size=int(parts.get("pool_size", 15)),
    )


@router.patch("/{tenant_id}", response_model=TenantResponse)
def update_tenant(tenant_id: str, tenant: TenantCreate):
    """Update tenant settings."""
    databases = parse_databases_ini()
    users = parse_userlist_txt()

    if tenant_id not in databases:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Update database config
    config = f"host={tenant.host} port={tenant.port} dbname={tenant.db_name} user={tenant.user} pool_size={tenant.pool_size}"
    databases[tenant_id] = config

    # Update user credentials
    users[tenant.user] = tenant.password

    save_databases(databases)
    save_userlist(users)

    return tenant


@router.delete("/{tenant_id}")
def delete_tenant(tenant_id: str):
    """Remove a tenant."""
    databases = parse_databases_ini()
    users = parse_userlist_txt()

    if tenant_id not in databases:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Remove from databases.ini
    del databases[tenant_id]

    # Remove from userlist.txt (find user to remove)
    for user, pass_hash in list(users.items()):
        if pass_hash == "REPLACE_ME":  # Placeholder - need better tracking
            del users[user]

    save_databases(databases)
    save_userlist(users)

    return {"message": "Tenant deleted"}
