"""Pool monitoring API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_service
from app.services.pgbouncer import PgBouncerError, PgBouncerService

router = APIRouter(prefix="/api/pools", tags=["pools"])
logger = logging.getLogger("pgbouncer_manager.audit")


def _to_int(value: str | None) -> int:
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


@router.get("/status")
def list_pools(svc: PgBouncerService = Depends(get_service)) -> dict[str, list[dict]]:
    """List pool statistics (SHOW POOLS)."""
    try:
        rows = svc.run_psql("SHOW POOLS;")
    except PgBouncerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    pools = [
        {
            "database": row.get("database", ""),
            "user": row.get("user", ""),
            "pool_mode": row.get("pool_mode", ""),
            "active": _to_int(row.get("cl_active") or row.get("sv_active")),
            "waiting": _to_int(row.get("cl_waiting")),
            "idle": _to_int(row.get("sv_idle")),
            "max_wait": _to_int(row.get("maxwait")),
        }
        for row in rows
    ]
    return {"pools": pools}


@router.get("/stats")
def list_stats(svc: PgBouncerService = Depends(get_service)) -> dict[str, list[dict]]:
    """List connection statistics (SHOW STATS)."""
    try:
        rows = svc.run_psql("SHOW STATS;")
    except PgBouncerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Return parsed rows verbatim (column names preserved) so the frontend can
    # display whatever PgBouncer reports without brittle positional parsing.
    return {"stats": rows}


@router.post("/reload")
def reload_pgbouncer(svc: PgBouncerService = Depends(get_service)) -> dict[str, str]:
    """Reload PgBouncer configuration (SIGHUP or admin RELOAD)."""
    try:
        message = svc.reload()
    except PgBouncerError as exc:
        logger.warning("config.reload failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    logger.info("config.reload %s", message)
    return {"status": "success", "message": message}
