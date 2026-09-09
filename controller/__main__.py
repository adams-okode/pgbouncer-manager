"""Entrypoint: ``python -m controller``.

Runs the kopf event loop in-process. The Helm chart deploys this as a single
replica -- the operator is the only writer of the config Secret, and two of
them would race exactly the way two managers on a shared volume do.
"""

from __future__ import annotations

import logging
import os
import sys

import kopf

from controller import handlers  # noqa: F401  -- importing registers the handlers


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("PGBM_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    namespace = os.environ.get("PGBM_NAMESPACE")
    kopf.run(
        # Empty means cluster-wide; the chart sets this when scoped to one
        # namespace so the operator's RBAC can be a Role rather than a
        # ClusterRole.
        namespaces=[namespace] if namespace else [],
        clusterwide=not namespace,
        standalone=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
