"""Connection-capacity reporting.

Answers "how many server connections have I committed against each target
Postgres, and is that safe?" without needing tenant credentials. Numbers come
from ``databases.ini``, refined with the admin console's effective settings
when PgBouncer is reachable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_service
from app.services.pgbouncer import PgBouncerService

router = APIRouter(prefix="/api/capacity", tags=["capacity"])


class TargetCapacityResponse(BaseModel):
    host: str
    port: int
    tenants: list[str]
    declared_total: int
    reserve_total: int
    worst_case_total: int
    current_connections: int | None = None
    max_connections: int | None = None
    headroom: int | None = None
    utilization: float | None = None
    status: str
    source: str
    unbounded_pools: list[str]


class CapacityResponse(BaseModel):
    targets: list[TargetCapacityResponse]


@router.get("", response_model=CapacityResponse)
def get_capacity(service: PgBouncerService = Depends(get_service)) -> CapacityResponse:
    """Report committed server connections per target host:port.

    Never fails on an unreachable admin console: capacity then reflects the
    declared config rather than PgBouncer's effective settings, which the
    ``source`` field distinguishes.
    """
    targets = [
        TargetCapacityResponse(**vars(target)) for target in service.capacity_by_target()
    ]
    return CapacityResponse(targets=targets)
