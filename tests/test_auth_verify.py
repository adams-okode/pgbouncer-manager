"""Tests for credential verification, which is what keeps reconciles idempotent."""

import pytest

from app import auth


@pytest.mark.parametrize("scheme", ["scram-sha-256", "md5", "plain"])
def test_verify_accepts_its_own_hash(scheme):
    stored = auth.hash_password("s3cret", "alice", scheme=scheme)
    assert auth.verify_password("s3cret", "alice", stored) is True


@pytest.mark.parametrize("scheme", ["scram-sha-256", "md5", "plain"])
def test_verify_rejects_wrong_password(scheme):
    stored = auth.hash_password("s3cret", "alice", scheme=scheme)
    assert auth.verify_password("guess", "alice", stored) is False


def test_verify_scram_is_salt_independent():
    """Two verifiers for one password differ, and both verify.

    This is the whole point: an operator that compared hashes for equality
    would see a change on every reconcile and reload PgBouncer forever.
    """
    first = auth.scram_sha256_hash("s3cret")
    second = auth.scram_sha256_hash("s3cret")
    assert first != second
    assert auth.verify_password("s3cret", "alice", first)
    assert auth.verify_password("s3cret", "alice", second)


def test_md5_verification_is_username_bound():
    stored = auth.md5_hash("s3cret", "alice")
    assert auth.verify_password("s3cret", "bob", stored) is False


def test_verify_respects_the_stored_iteration_count():
    stored = auth.scram_sha256_hash("s3cret", iterations=1024)
    assert auth.verify_password("s3cret", "alice", stored) is True


@pytest.mark.parametrize(
    "stored",
    [
        "SCRAM-SHA-256$",
        "SCRAM-SHA-256$notanint:c2FsdA==$a:b",
        "SCRAM-SHA-256$4096:!!!!$a:b",
        "SCRAM-SHA-256$4096:c2FsdA==$onlyone",
    ],
)
def test_malformed_verifier_is_rejected_not_raised(stored):
    assert auth.verify_password("s3cret", "alice", stored) is False


def test_absurd_iteration_count_is_refused_without_computing_it():
    """An attacker-supplied iteration count must not become a CPU bomb."""
    stored = f"SCRAM-SHA-256${10**9}:c2FsdA==$a:b"
    assert auth.verify_password("s3cret", "alice", stored) is False
