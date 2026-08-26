"""Capacity accounting: pure arithmetic over databases.ini, refined by SHOW DATABASES."""

import pytest

from app.config import Settings
from app.services.pgbouncer import PgBouncerError, PgBouncerService


@pytest.fixture
def make_service(tmp_path):
    def _make(entries: str, **overrides):
        (tmp_path / "databases.ini").write_text(f"[databases]\n{entries}\n")
        settings = Settings(config_dir=tmp_path, **overrides)
        return PgBouncerService(settings)

    return _make


def _no_console(service):
    """Simulate an unreachable admin console."""
    def _raise(_query):
        raise PgBouncerError("connection refused")

    service.run_psql = _raise


def test_sums_pool_size_across_tenants_on_one_target(make_service):
    svc = make_service(
        "a = host=db1 port=5432 dbname=x user=u pool_size=15\n"
        "b = host=db1 port=5432 dbname=y user=u pool_size=25"
    )
    _no_console(svc)
    (target,) = svc.capacity_by_target()

    assert (target.host, target.port) == ("db1", 5432)
    assert target.tenants == ["a", "b"]
    # Each entry is its own pool, so the sizes add rather than overlap.
    assert target.declared_total == 40
    assert target.source == "databases.ini"


def test_splits_targets_by_host_and_port(make_service):
    svc = make_service(
        "a = host=db1 port=5432 dbname=x user=u pool_size=10\n"
        "b = host=db1 port=6432 dbname=x user=u pool_size=10\n"
        "c = host=db2 port=5432 dbname=x user=u pool_size=10"
    )
    _no_console(svc)
    targets = svc.capacity_by_target()

    assert [(t.host, t.port) for t in targets] == [("db1", 5432), ("db1", 6432), ("db2", 5432)]


def test_missing_pool_size_falls_back_to_pgbouncer_default(make_service):
    svc = make_service("a = host=db1 port=5432 dbname=x user=u")
    _no_console(svc)
    (target,) = svc.capacity_by_target()

    # PgBouncer's default_pool_size, not this tool's default for new tenants.
    assert target.declared_total == 20


def test_status_unknown_without_a_configured_limit(make_service):
    svc = make_service("a = host=db1 port=5432 dbname=x user=u pool_size=10")
    _no_console(svc)
    (target,) = svc.capacity_by_target()

    assert target.status == "unknown"
    assert target.max_connections is None
    assert target.headroom is None


def test_status_ok_with_headroom(make_service):
    svc = make_service(
        "a = host=db1 port=5432 dbname=x user=u pool_size=10",
        capacity_limits={"db1:5432": 100},
    )
    _no_console(svc)
    (target,) = svc.capacity_by_target()

    # 100 - 3 superuser-reserved = 97 usable, minus 10 committed.
    assert target.headroom == 87
    assert target.status == "ok"


def test_status_tight_near_the_ceiling(make_service):
    svc = make_service(
        "a = host=db1 port=5432 dbname=x user=u pool_size=80",
        capacity_limits={"db1:5432": 100},
    )
    _no_console(svc)
    (target,) = svc.capacity_by_target()

    assert target.status == "tight"
    assert target.headroom == 17


def test_status_oversubscribed_beyond_the_ceiling(make_service):
    svc = make_service(
        "a = host=db1 port=5432 dbname=x user=u pool_size=60\n"
        "b = host=db1 port=5432 dbname=y user=u pool_size=60",
        capacity_limits={"db1:5432": 100},
    )
    _no_console(svc)
    (target,) = svc.capacity_by_target()

    assert target.declared_total == 120
    assert target.headroom == -23
    assert target.status == "oversubscribed"


def test_entry_without_forced_user_is_flagged_unbounded(make_service):
    svc = make_service(
        "a = host=db1 port=5432 dbname=x pool_size=10\n"
        "b = host=db1 port=5432 dbname=y user=u pool_size=10"
    )
    _no_console(svc)
    (target,) = svc.capacity_by_target()

    # 'a' has no user=, so PgBouncer opens a pool per connecting user.
    assert target.unbounded_pools == ["a"]


def test_console_values_override_the_declared_config(make_service):
    svc = make_service(
        "a = host=db1 port=5432 dbname=x user=u pool_size=10",
        capacity_limits={"db1:5432": 100},
    )
    svc.run_psql = lambda _q: [
        {
            "name": "a",
            "pool_size": "40",
            "reserve_pool": "5",
            "current_connections": "7",
        }
    ]
    (target,) = svc.capacity_by_target()

    assert target.declared_total == 40          # console wins over the ini's 10
    assert target.reserve_total == 5
    assert target.worst_case_total == 45        # reserve stacks on top of pool_size
    assert target.current_connections == 7
    assert target.source == "pgbouncer"


def test_reserve_pool_size_column_alias_is_understood(make_service):
    svc = make_service("a = host=db1 port=5432 dbname=x user=u pool_size=10")
    svc.run_psql = lambda _q: [
        {"name": "a", "pool_size": "10", "reserve_pool_size": "3"}
    ]
    (target,) = svc.capacity_by_target()

    assert target.reserve_total == 3


def test_unreachable_console_still_reports_declared_capacity(make_service):
    svc = make_service("a = host=db1 port=5432 dbname=x user=u pool_size=10")
    _no_console(svc)
    (target,) = svc.capacity_by_target()

    assert target.declared_total == 10
    assert target.source == "databases.ini"


def test_no_tenants_yields_no_targets(make_service):
    svc = make_service("")
    _no_console(svc)
    assert svc.capacity_by_target() == []
