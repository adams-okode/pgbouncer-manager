"""Pool monitoring API endpoints."""

import subprocess

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/pools", tags=["pools"])


def run_psql(query: str) -> list[str]:
    """Run psql command and return output lines."""
    try:
        result = subprocess.run(
            ["psql", "-h", "localhost", "-p", "6543", "-U", "pgbouncer", "-d", "pgbouncer", "-c", query],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.split("\n")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="PgBouncer query timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="psql not found")


def parse_pools_output(lines: list[str]) -> list[dict]:
    """Parse SHOW POOLS output into structured data."""
    pools = []
    for line in lines:
        if not line or line.startswith(("Database", "Total")):
            continue
        parts = line.split()
        if len(parts) >= 7:
            pools.append({
                "database": parts[0],
                "user": parts[1],
                "pool_mode": parts[2],
                "active": int(parts[3]) if parts[3].isdigit() else 0,
                "waiting": int(parts[4]) if parts[4].isdigit() else 0,
                "idle": int(parts[5]) if parts[5].isdigit() else 0,
                "max_wait": int(parts[6]) if parts[6].isdigit() else 0,
            })
    return pools


def parse_stats_output(lines: list[str]) -> list[dict]:
    """Parse SHOW STATS output into structured data."""
    stats = []
    for line in lines:
        if not line or line.startswith(("Total", "Total connection usage")):
            continue
        parts = line.split()
        if len(parts) >= 20:
            stats.append({
                "database": parts[0],
                "user": parts[1],
                "type": parts[2],
                "state": parts[3],
                "addr": parts[4],
                "port": int(parts[5]) if parts[5].isdigit() else 0,
            })
    return stats


@router.get("/status")
def list_pools():
    """List pool statistics."""
    lines = run_psql("SHOW POOLS;")
    pools = parse_pools_output(lines)
    return {"pools": pools}


@router.get("/stats")
def list_stats():
    """List connection statistics."""
    lines = run_psql("SHOW STATS;")
    stats = parse_stats_output(lines)
    return {"stats": stats}


@router.post("/reload")
def reload_pgbouncer():
    """Reload PgBouncer configuration."""
    try:
        result = subprocess.run(
            ["docker", "kill", "--signal=HUP", "pgbouncer-tx", "pgbouncer-session"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return {"status": "success", "message": "PgBouncer reloaded"}
        return {"status": "error", "message": result.stderr or "Unknown error"}
    except FileNotFoundError:
        # Fall back to psql reload if docker not available
        try:
            run_psql("RELOAD;")
            return {"status": "success", "message": "PgBouncer reloaded via psql"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
