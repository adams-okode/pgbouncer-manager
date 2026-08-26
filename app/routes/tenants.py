"""Tenant management API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import get_service
from app.services.pgbouncer import PgBouncerService, validate_tenant_id

router = APIRouter(prefix="/api/tenants", tags=["tenants"])
logger = logging.getLogger("pgbouncer_manager.audit")

_DEFAULT_POOL_SIZE = 15


class TenantCreate(BaseModel):
    id: str
    host: str
    port: int = 5432
    db_name: str = "postgres"
    user: str = "postgres"
    password: str
    pool_size: int = _DEFAULT_POOL_SIZE
    pool_mode: str | None = None


class TenantUpdate(BaseModel):
    """Partial update. Every field is optional; only provided fields change."""

    host: str | None = None
    port: int | None = None
    db_name: str | None = None
    user: str | None = None
    password: str | None = Field(default=None, min_length=1)
    pool_size: int | None = None
    pool_mode: str | None = None


class TenantResponse(BaseModel):
    id: str
    host: str
    port: int
    db_name: str
    user: str
    pool_size: int
    pool_mode: str | None = None


def _to_response(tenant_id: str, parts: dict[str, str]) -> TenantResponse:
    return TenantResponse(
        id=tenant_id,
        host=parts.get("host", ""),
        port=int(parts.get("port", 5432)),
        db_name=parts.get("dbname", "postgres"),
        user=parts.get("user", "postgres"),
        pool_size=int(parts.get("pool_size", _DEFAULT_POOL_SIZE)),
        pool_mode=parts.get("pool_mode"),
    )


def _build_parts(
    *, host: str, port: int, db_name: str, user: str, pool_size: int,
    pool_mode: str | None,
) -> dict[str, str]:
    parts = {
        "host": host,
        "port": str(port),
        "dbname": db_name,
        "user": user,
        "pool_size": str(pool_size),
    }
    if pool_mode:
        parts["pool_mode"] = pool_mode
    return parts


def _user_still_referenced(
    databases: dict[str, dict[str, str]], user: str, *, exclude: str | None = None
) -> bool:
    return any(
        parts.get("user") == user
        for tid, parts in databases.items()
        if tid != exclude
    )


@router.get("", response_model=list[TenantResponse])
def list_tenants(svc: PgBouncerService = Depends(get_service)) -> list[TenantResponse]:
    """List all tenants."""
    databases = svc.read_databases()
    return [_to_response(tid, parts) for tid, parts in databases.items()]


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: str, svc: PgBouncerService = Depends(get_service)
) -> TenantResponse:
    """Get tenant details."""
    databases = svc.read_databases()
    if tenant_id not in databases:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _to_response(tenant_id, databases[tenant_id])


@router.post("", response_model=TenantResponse, status_code=201)
def add_tenant(
    tenant: TenantCreate, svc: PgBouncerService = Depends(get_service)
) -> TenantResponse:
    """Add a new tenant."""
    try:
        validate_tenant_id(tenant.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    databases = svc.read_databases()
    if tenant.id in databases:
        raise HTTPException(status_code=409, detail="Tenant already exists")

    users = svc.read_userlist()
    databases[tenant.id] = _build_parts(
        host=tenant.host, port=tenant.port, db_name=tenant.db_name,
        user=tenant.user, pool_size=tenant.pool_size, pool_mode=tenant.pool_mode,
    )
    users[tenant.user] = svc.hash_credential(tenant.password, tenant.user)

    svc.write_databases(databases)
    svc.write_userlist(users)
    logger.info("tenant.add id=%s user=%s", tenant.id, tenant.user)
    return _to_response(tenant.id, databases[tenant.id])


@router.patch("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: str,
    update: TenantUpdate,
    svc: PgBouncerService = Depends(get_service),
) -> TenantResponse:
    """Partially update an existing tenant."""
    databases = svc.read_databases()
    if tenant_id not in databases:
        raise HTTPException(status_code=404, detail="Tenant not found")

    parts = databases[tenant_id]
    old_user = parts.get("user", "postgres")

    if update.host is not None:
        parts["host"] = update.host
    if update.port is not None:
        parts["port"] = str(update.port)
    if update.db_name is not None:
        parts["dbname"] = update.db_name
    if update.user is not None:
        parts["user"] = update.user
    if update.pool_size is not None:
        parts["pool_size"] = str(update.pool_size)
    if update.pool_mode is not None:
        parts["pool_mode"] = update.pool_mode

    databases[tenant_id] = parts
    new_user = parts.get("user", old_user)

    users = svc.read_userlist()
    credential_changed = False
    if update.password is not None:
        users[new_user] = svc.hash_credential(update.password, new_user)
        credential_changed = True

    # If the user was renamed, drop the stale entry when nothing else uses it.
    if new_user != old_user and not _user_still_referenced(databases, old_user):
        users.pop(old_user, None)

    svc.write_databases(databases)
    svc.write_userlist(users)
    logger.info(
        "tenant.update id=%s user=%s credential_changed=%s",
        tenant_id, new_user, credential_changed,
    )
    return _to_response(tenant_id, parts)


@router.delete("/{tenant_id}")
def delete_tenant(
    tenant_id: str, svc: PgBouncerService = Depends(get_service)
) -> dict[str, str]:
    """Remove a tenant and its (now-unused) credential."""
    databases = svc.read_databases()
    if tenant_id not in databases:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user = databases[tenant_id].get("user", "")
    del databases[tenant_id]

    users = svc.read_userlist()
    if user and not _user_still_referenced(databases, user):
        users.pop(user, None)

    svc.write_databases(databases)
    svc.write_userlist(users)
    logger.info("tenant.remove id=%s user=%s", tenant_id, user)
    return {"message": "Tenant deleted", "id": tenant_id}
