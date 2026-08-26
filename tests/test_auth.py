"""Tests for credential hashing."""

import hashlib

from app import auth


def test_md5_hash_format():
    expected = "md5" + hashlib.md5(b"secretalice").hexdigest()
    assert auth.md5_hash("secret", "alice") == expected
    assert auth.is_already_hashed(auth.md5_hash("secret", "alice"))


def test_scram_hash_structure_and_determinism():
    salt = b"\x01" * 16
    first = auth.scram_sha256_hash("secret", iterations=4096, salt=salt)
    second = auth.scram_sha256_hash("secret", iterations=4096, salt=salt)
    assert first == second  # same salt -> same verifier
    assert first.startswith("SCRAM-SHA-256$4096:")
    # Format: SCRAM-SHA-256$<iter>:<salt>$<stored>:<server>
    _scheme_iter, rest = first.split(":", 1)
    salt_part, keys = rest.split("$", 1)
    stored, server = keys.split(":")
    assert salt_part and stored and server
    assert auth.is_already_hashed(first)


def test_scram_random_salt_differs():
    a = auth.scram_sha256_hash("secret")
    b = auth.scram_sha256_hash("secret")
    assert a != b  # random salt each call


def test_hash_password_dispatch():
    assert auth.hash_password("p", "u", scheme="plain") == "p"
    assert auth.hash_password("p", "u", scheme="md5").startswith("md5")
    assert auth.hash_password("p", "u", scheme="scram-sha-256").startswith("SCRAM-SHA-256$")


def test_is_already_hashed_false_for_plaintext():
    assert not auth.is_already_hashed("justapassword")
