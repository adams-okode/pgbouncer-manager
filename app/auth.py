"""Generate PgBouncer-compatible credential hashes for ``userlist.txt``.

PgBouncer never stores raw passwords. It accepts two hashed formats:

* **md5** -- ``"md5" + md5(password + username)`` (legacy, still widely used).
* **SCRAM-SHA-256** -- the modern, salted, iterated format also used by
  PostgreSQL 10+. The verifier string is::

      SCRAM-SHA-256$<iterations>:<b64 salt>$<b64 StoredKey>:<b64 ServerKey>

A ``"plain"`` scheme is also supported but should only ever be used for local
testing -- it stores the password verbatim and is not recommended.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

_SCRAM_DEFAULT_ITERATIONS = 4096
_SCRAM_SALT_BYTES = 16


def md5_hash(password: str, username: str) -> str:
    """Return a PgBouncer md5 credential string."""
    digest = hashlib.md5((password + username).encode("utf-8")).hexdigest()
    return f"md5{digest}"


def scram_sha256_hash(
    password: str,
    *,
    iterations: int = _SCRAM_DEFAULT_ITERATIONS,
    salt: bytes | None = None,
) -> str:
    """Return a SCRAM-SHA-256 verifier string for ``password``.

    ``salt`` is only injected for deterministic testing; in normal use a fresh
    random salt is generated for every call.
    """
    if salt is None:
        salt = os.urandom(_SCRAM_SALT_BYTES)

    salted_password = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations, dklen=32
    )
    client_key = hmac.new(salted_password, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted_password, b"Server Key", hashlib.sha256).digest()

    b64_salt = base64.b64encode(salt).decode("ascii")
    b64_stored = base64.b64encode(stored_key).decode("ascii")
    b64_server = base64.b64encode(server_key).decode("ascii")
    return f"SCRAM-SHA-256${iterations}:{b64_salt}${b64_stored}:{b64_server}"


def hash_password(
    password: str,
    username: str,
    *,
    scheme: str = "scram-sha-256",
    iterations: int = _SCRAM_DEFAULT_ITERATIONS,
) -> str:
    """Hash ``password`` according to ``scheme`` for storage in userlist.txt."""
    scheme = scheme.strip().lower()
    if scheme == "scram-sha-256":
        return scram_sha256_hash(password, iterations=iterations)
    if scheme == "md5":
        return md5_hash(password, username)
    if scheme == "plain":
        return password
    raise ValueError(f"Unsupported auth scheme: {scheme!r}")


def is_already_hashed(value: str) -> bool:
    """Best-effort detection of an already-hashed credential.

    Used to avoid double-hashing a value that a caller supplied pre-hashed.
    """
    return value.startswith("md5") or value.startswith("SCRAM-SHA-256$")
