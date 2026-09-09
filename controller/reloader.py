"""Sidecar that reloads PgBouncer in place when its mounted config changes.

Runs beside PgBouncer in the pooler pod and does one thing: notice that the
kubelet has refreshed the config Secret, and send ``SIGHUP`` to the PgBouncer
process, which re-reads its files without dropping established client
connections.

The alternative -- putting a config checksum on the pod template so the
Deployment rolls -- is simpler but interrupts every pooled session for every
tenant change. On a pooler that is the whole cost model: adding one tenant
should not disconnect the other hundred.

Signalling across containers needs ``shareProcessNamespace: true`` on the pod,
which the operator sets when this sidecar is used. Both containers run as the
same UID, so no privileges beyond "signal your own processes" are required.
"""

from __future__ import annotations

import hashlib
import logging
import os
import signal
import sys
import time
from pathlib import Path

logger = logging.getLogger("pgbouncer_manager.reloader")

DEFAULT_WATCH_DIR = "/etc/pgbouncer"
DEFAULT_INTERVAL = 10.0
PROCESS_NAME = "pgbouncer"

_running = True


def _stop(signum: int, _frame: object) -> None:
    global _running
    logger.info("received signal %s, stopping", signum)
    _running = False


def config_digest(watch_dir: Path) -> str:
    """Digest of every regular file in ``watch_dir``.

    A Secret volume is a directory of symlinks into a hidden ``..data``
    directory that the kubelet swaps atomically, so the file names stay put
    while the contents change underneath. Reading through them is what detects
    an update; watching mtimes on the symlinks themselves does not.
    """
    digest = hashlib.sha256()
    try:
        names = sorted(p for p in watch_dir.iterdir() if p.is_file())
    except OSError as exc:
        logger.warning("cannot read %s: %s", watch_dir, exc)
        return ""
    for path in names:
        try:
            content = path.read_bytes()
        except OSError:
            # A file mid-swap: skip it and let the next tick see a stable set.
            continue
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
    return digest.hexdigest()


def find_pgbouncer_pids() -> list[int]:
    """PIDs of PgBouncer processes visible in this (shared) namespace."""
    pids: list[int] = []
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            comm = (entry / "comm").read_text(encoding="utf-8").strip()
        except OSError:
            # The process exited between listdir and read.
            continue
        if comm == PROCESS_NAME:
            pids.append(int(entry.name))
    return sorted(pids)


def reload_pgbouncer() -> int:
    """SIGHUP every PgBouncer process found. Returns how many were signalled."""
    pids = find_pgbouncer_pids()
    if not pids:
        logger.warning(
            "config changed but no %r process is visible; is "
            "shareProcessNamespace enabled on the pod?",
            PROCESS_NAME,
        )
        return 0
    signalled = 0
    for pid in pids:
        try:
            os.kill(pid, signal.SIGHUP)
        except (ProcessLookupError, PermissionError) as exc:
            logger.warning("cannot signal pid %d: %s", pid, exc)
            continue
        signalled += 1
        logger.info("sent SIGHUP to pgbouncer pid %d", pid)
    return signalled


def watch(watch_dir: Path, interval: float) -> None:
    """Poll ``watch_dir`` and reload PgBouncer whenever its content changes."""
    # PgBouncer started with the config that is on disk right now, so the first
    # observation is the baseline, not a change.
    last = config_digest(watch_dir)
    logger.info(
        "watching %s every %.0fs (baseline %s)", watch_dir, interval, last[:12] or "empty"
    )
    while _running:
        time.sleep(interval)
        if not _running:
            break
        current = config_digest(watch_dir)
        if not current or current == last:
            continue
        logger.info("config changed (%s -> %s)", last[:12], current[:12])
        if reload_pgbouncer():
            last = current


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    watch_dir = Path(os.environ.get("PGBM_WATCH_DIR", DEFAULT_WATCH_DIR))
    try:
        interval = float(os.environ.get("PGBM_RELOAD_INTERVAL", DEFAULT_INTERVAL))
    except ValueError:
        interval = DEFAULT_INTERVAL
    if interval <= 0:
        interval = DEFAULT_INTERVAL

    watch(watch_dir, interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
