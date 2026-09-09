"""Generate PgBouncer-compatible credential hashes for ``userlist.txt``.

PgBouncer never stores raw passwords. It accepts two hashed formats:

* **md5** -- ``"md5" + md5(password + username)`` (legacy, still widely used).
* **SCRAM-SHA-256** -- the modern, salted, iterated format also used by
  PostgreSQL 10+. The verifier string is::

      SCRAM-SHA-256$<iterations>:<b64 salt>$<b64 StoredKey>:<b64 ServerKey>

A ``"plain"`` scheme is also supported but should only ever be used for local
testing -- it stores the password verbatim and is not recommended.

:func:`verify_password` answers the inverse question -- "is this stored
credential already the one for this password?" -- which a reconciling caller
needs in order to leave a matching entry alone instead of re-salting it.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import re

_SCRAM_DEFAULT_ITERATIONS = 4096
_SCRAM_SALT_BYTES = 16

_SCRAM_VERIFIER_RE = re.compile(
    r"^SCRAM-SHA-256\$(\d+):([A-Za-z0-9+/=]+)\$([A-Za-z0-9+/=]+):([A-Za-z0-9+/=]+)$"
)
# A verifier carries its own iteration count, and we re-run PBKDF2 with it to
# check a candidate password. That makes the count attacker-controlled if the
# stored file is, so refuse an absurd one rather than burning CPU on it.
_SCRAM_MAX_ITERATIONS = 1_000_000


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
    return value.startswith(("md5", "SCRAM-SHA-256$"))


def verify_password(password: str, username: str, stored: str) -> bool:
    """Return True when ``stored`` is already a credential for ``password``.

    The format is detected from ``stored`` itself rather than taken from the
    configured ``auth_scheme``: a userlist can legitimately hold a mixture of
    formats after a scheme change, and the point of this function is to decide
    whether an entry can be left untouched.

    This matters because SCRAM verifiers are salted. Re-hashing an unchanged
    password produces a *different* verifier every time, so a caller that
    reconciles desired state against a rendered file (the Kubernetes operator,
    or ``apply``) would otherwise report a diff and trigger a PgBouncer reload
    on every single pass. Verifying instead of re-hashing keeps those runs
    idempotent.
    """
    if stored.startswith("SCRAM-SHA-256$"):
        match = _SCRAM_VERIFIER_RE.match(stored)
        if match is None:
            return False
        iterations = int(match.group(1))
        if not 0 < iterations <= _SCRAM_MAX_ITERATIONS:
            return False
        try:
            salt = base64.b64decode(match.group(2), validate=True)
        except (binascii.Error, ValueError):
            return False
        candidate = scram_sha256_hash(password, iterations=iterations, salt=salt)
        return hmac.compare_digest(candidate, stored)

    if stored.startswith("md5"):
        return hmac.compare_digest(md5_hash(password, username), stored)

    # Anything else is a plain-scheme entry: the password verbatim.
    return hmac.compare_digest(stored, password)
