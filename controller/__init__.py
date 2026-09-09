"""Kubernetes operator for PgBouncer poolers.

The package is called ``controller`` rather than ``operator`` on purpose:
``operator`` is a standard-library module, and shadowing it from the repo root
breaks any dependency that imports it.

Why an operator at all -- the rest of this project is built on "PgBouncer's
config files are the state", with one writer editing a shared volume. That
model does not survive Kubernetes: pods are ephemeral, ReadWriteMany volumes
are rare, and two manager replicas on one volume race. So in the cluster the
source of truth moves up to the Kubernetes API. Custom resources are the
desired state, the operator renders them into a Secret, and PgBouncer mounts
it. The domain logic -- SCRAM hashing, the connect-string format, the capacity
arithmetic -- is unchanged and shared with the file-based path.
"""
