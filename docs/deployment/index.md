# Deployment

Three deployment models, one domain model. What changes between them is where
the desired state lives, not what the config means.

| | Where state lives | How you change it | Reload |
|---|---|---|---|
| [Kubernetes](kubernetes.md) | `PgBouncerDatabase` resources | `kubectl` / `helm upgrade` | in-place `SIGHUP` from a sidecar |
| [Docker](docker.md) | `databases.ini` on a shared volume | API, CLI, or `apply -f tenants.yaml` | admin-console `RELOAD` |
| [Bare metal](bare-metal.md) | `databases.ini` on disk | API, CLI, or `apply -f tenants.yaml` | admin-console `RELOAD` or `SIGHUP` |

The declarative schema is shared: a `tenants.yaml` entry and a
`PgBouncerDatabase` spec have the same fields, so moving a deployment from
Compose to a cluster is a translation rather than a redesign.

- [Docker](docker.md) — including a [hardened Compose stack](docker.md#hardened-compose-stack)
- [Kubernetes](kubernetes.md) — the operator
- [Helm chart](helm.md) — every value
- [Bare Metal](bare-metal.md)
