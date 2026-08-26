"""CLI for tenant management -- a thin HTTP client of the FastAPI backend.

Uses only the standard library (``urllib``) so the CLI ships with no extra
runtime dependencies. The API base URL is configurable via ``--api-url`` or the
``PGBM_API_URL`` environment variable (default: ``http://localhost:3000``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_API_URL = "http://localhost:3000"


class ApiError(RuntimeError):
    """Raised when the API returns a non-2xx response."""


def _request(api_url: str, method: str, path: str, payload: dict | None = None) -> object:
    url = f"{api_url.rstrip('/')}/api{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # URL is operator-supplied
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except json.JSONDecodeError:
            pass
        raise ApiError(f"{exc.code} {exc.reason}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"Could not reach API at {url}: {exc.reason}") from exc
    return json.loads(body) if body else None


def _print_json(obj: object) -> None:
    print(json.dumps(obj, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PgBouncer Tenant Manager CLI", prog="pgbouncer-manager"
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("PGBM_API_URL", DEFAULT_API_URL),
        help="Base URL of the PgBouncer Manager API",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    add = sub.add_parser("tenant-add", help="Add a new tenant")
    add.add_argument("--id", required=True)
    add.add_argument("--host", required=True)
    add.add_argument("--port", type=int, default=5432)
    add.add_argument("--db-name", default="postgres")
    add.add_argument("--user", default="postgres")
    add.add_argument("--password", required=True)
    add.add_argument("--pool-size", type=int, default=15)
    add.add_argument("--pool-mode")

    upd = sub.add_parser("tenant-update", help="Update a tenant")
    upd.add_argument("--id", required=True)
    upd.add_argument("--host")
    upd.add_argument("--port", type=int)
    upd.add_argument("--db-name")
    upd.add_argument("--user")
    upd.add_argument("--password")
    upd.add_argument("--pool-size", type=int)
    upd.add_argument("--pool-mode")

    rm = sub.add_parser("tenant-remove", help="Remove a tenant")
    rm.add_argument("--id", required=True)

    get = sub.add_parser("tenant-get", help="Get one tenant")
    get.add_argument("--id", required=True)

    sub.add_parser("tenant-list", help="List all tenants")
    sub.add_parser("pools-list", help="List pool statistics")
    sub.add_parser("stats-list", help="List connection statistics")
    sub.add_parser("reload", help="Reload PgBouncer")
    return parser


def run(args: argparse.Namespace) -> int:
    api = args.api_url
    cmd = args.command

    if cmd == "tenant-add":
        payload = {
            "id": args.id,
            "host": args.host,
            "port": args.port,
            "db_name": args.db_name,
            "user": args.user,
            "password": args.password,
            "pool_size": args.pool_size,
        }
        if args.pool_mode:
            payload["pool_mode"] = args.pool_mode
        _print_json(_request(api, "POST", "/tenants", payload))

    elif cmd == "tenant-update":
        update_payload: dict[str, object] = {}
        for field in ("host", "port", "db_name", "user", "password", "pool_size", "pool_mode"):
            value = getattr(args, field.replace("-", "_"))
            if value is not None:
                update_payload[field] = value
        if not update_payload:
            print("Nothing to update: provide at least one field.", file=sys.stderr)
            return 2
        _print_json(_request(api, "PATCH", f"/tenants/{args.id}", update_payload))

    elif cmd == "tenant-remove":
        _print_json(_request(api, "DELETE", f"/tenants/{args.id}"))

    elif cmd == "tenant-get":
        _print_json(_request(api, "GET", f"/tenants/{args.id}"))

    elif cmd == "tenant-list":
        _print_json(_request(api, "GET", "/tenants"))

    elif cmd == "pools-list":
        _print_json(_request(api, "GET", "/pools/status"))

    elif cmd == "stats-list":
        _print_json(_request(api, "GET", "/pools/stats"))

    elif cmd == "reload":
        _print_json(_request(api, "POST", "/pools/reload"))

    else:
        return 1
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        raise SystemExit(1)
    try:
        raise SystemExit(run(args))
    except ApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
