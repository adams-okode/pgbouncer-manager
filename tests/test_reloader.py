"""Tests for the reload sidecar's change detection."""

from controller import reloader


def test_digest_changes_when_content_changes(tmp_path):
    (tmp_path / "databases.ini").write_text("[databases]\n")
    before = reloader.config_digest(tmp_path)

    (tmp_path / "databases.ini").write_text("[databases]\nacme = host=db1\n")
    assert reloader.config_digest(tmp_path) != before


def test_digest_is_stable_for_unchanged_content(tmp_path):
    (tmp_path / "databases.ini").write_text("[databases]\n")
    assert reloader.config_digest(tmp_path) == reloader.config_digest(tmp_path)


def test_digest_covers_every_file_in_the_directory(tmp_path):
    (tmp_path / "databases.ini").write_text("[databases]\n")
    before = reloader.config_digest(tmp_path)

    # A rotated password changes only userlist.txt; that must still count.
    (tmp_path / "userlist.txt").write_text('"acme" "md5abc"\n')
    assert reloader.config_digest(tmp_path) != before


def test_missing_directory_yields_an_empty_digest(tmp_path):
    """An empty digest is treated as 'no reading', never as 'config emptied' -
    reloading PgBouncer against a vanished mount would be worse than waiting.
    """
    assert reloader.config_digest(tmp_path / "absent") == ""


def test_reload_reports_zero_when_no_pgbouncer_is_visible(monkeypatch):
    monkeypatch.setattr(reloader, "find_pgbouncer_pids", list)
    assert reloader.reload_pgbouncer() == 0


def test_reload_signals_every_pgbouncer_process(monkeypatch):
    signalled = []
    monkeypatch.setattr(reloader, "find_pgbouncer_pids", lambda: [11, 12])
    monkeypatch.setattr(reloader.os, "kill", lambda pid, sig: signalled.append((pid, sig)))

    assert reloader.reload_pgbouncer() == 2
    assert [pid for pid, _ in signalled] == [11, 12]
    assert {sig for _, sig in signalled} == {reloader.signal.SIGHUP}
