"""Tests for config rendering, including the injection defences."""

import pytest

from app.services import render


def test_renders_databases_section():
    text = render.render_databases_ini(
        {"acme": {"host": "db1", "port": "5432", "user": "acme"}}
    )
    assert text.splitlines() == [
        "[databases]",
        "acme = host=db1 port=5432 user=acme",
    ]


def test_renders_userlist_with_quoted_fields():
    text = render.render_userlist({"alice": "md5abc"})
    assert '"alice" "md5abc"' in text


def test_pgbouncer_ini_includes_the_databases_file():
    text = render.render_pgbouncer_ini({"pool_mode": "transaction"}, include="/etc/pgbouncer/databases.ini")
    assert "[pgbouncer]" in text
    assert "pool_mode = transaction" in text
    assert text.rstrip().endswith("%include /etc/pgbouncer/databases.ini")


@pytest.mark.parametrize(
    "value",
    [
        "db1 pool_size=9999",       # a second connect-string option
        "db1\nevil = host=x",       # a whole new entry
        "",                          # empty makes the line unparseable
    ],
)
def test_databases_value_injection_is_rejected(value):
    with pytest.raises(render.ConfigValueError):
        render.render_databases_ini({"acme": {"host": value}})


def test_databases_key_injection_is_rejected():
    with pytest.raises(render.ConfigValueError):
        render.render_databases_ini({"acme": {"host=db1 user": "x"}})


def test_pgbouncer_ini_value_may_not_span_lines():
    """The escalation this blocks: a newline appends `auth_type = trust`."""
    with pytest.raises(render.ConfigValueError):
        render.render_pgbouncer_ini({"pool_mode": "transaction\nauth_type = trust"})


def test_userlist_rejects_a_quote_in_either_field():
    with pytest.raises(render.ConfigValueError):
        render.render_userlist({'ali"ce': "md5abc"})
    with pytest.raises(render.ConfigValueError):
        render.render_userlist({"alice": 'md5a"bc'})
