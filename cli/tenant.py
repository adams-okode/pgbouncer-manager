"""CLI commands for tenant management."""

import argparse


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="PgBouncer Tenant Manager CLI",
        prog="pgbouncer-manager",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add tenant
    add_parser = subparsers.add_parser("tenant-add", help="Add a new tenant")
    add_parser.add_argument("--id", required=True, help="Tenant ID")
    add_parser.add_argument("--host", required=True, help="Database host")
    add_parser.add_argument("--user", default="postgres", help="Database user")
    add_parser.add_argument("--password", required=True, help="Database password")
    add_parser.add_argument("--pool-size", type=int, default=15, help="Pool size")

    # Update tenant
    update_parser = subparsers.add_parser("tenant-update", help="Update tenant")
    update_parser.add_argument("--id", required=True, help="Tenant ID")
    update_parser.add_argument("--pool-size", type=int, help="New pool size")
    update_parser.add_argument("--password", help="New password")

    # Remove tenant
    remove_parser = subparsers.add_parser("tenant-remove", help="Remove a tenant")
    remove_parser.add_argument("--id", required=True, help="Tenant ID")

    # List tenants
    subparsers.add_parser("tenant-list", help="List all tenants")

    # Pool list
    subparsers.add_parser("pools-list", help="List pool statistics")

    # Reload
    subparsers.add_parser("reload", help="Reload PgBouncer")

    return parser.parse_args()


def main():
    """Main CLI entry point."""
    args = parse_args()

    if args.command == "tenant-add":
        print(f"Adding tenant: {args.id} @ {args.host}")
        print(f"User: {args.user}, Pool Size: {args.pool_size}")
        print(f"Password: {'*' * len(args.password)}")

    elif args.command == "tenant-list":
        print("Listing tenants...")
        # TODO: Implement actual list logic

    elif args.command == "tenant-update":
        print(f"Updating tenant: {args.id}")
        if args.pool_size:
            print(f"New pool size: {args.pool_size}")
        if args.password:
            print(f"New password: {'*' * len(args.password)}")

    elif args.command == "tenant-remove":
        print(f"Removing tenant: {args.id}")

    elif args.command == "pools-list":
        print("Pool Statistics:")
        print("Tenant       | Mode         | Active | Waiting | Idle")
        print("-------------|--------------|--------|---------|------")

    elif args.command == "reload":
        print("Sending SIGHUP to PgBouncer containers...")
        print("Reload complete.")

    else:
        print("Usage: pgbouncer-manager [command]")
        print("Available commands: tenant-add, tenant-list, tenant-update, tenant-remove, pools-list, reload")


if __name__ == "__main__":
    main()
