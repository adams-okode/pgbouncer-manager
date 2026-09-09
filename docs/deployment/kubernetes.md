# Kubernetes

On Kubernetes this project runs as an **operator**. You declare poolers and
databases as custom resources; the operator renders them into PgBouncer config
and keeps a hardened PgBouncer deployment serving it.

## Why the model changes here

Everywhere else in this project, [PgBouncer's config files *are* the
state](../index.md): one manager process edits `databases.ini` and
`userlist.txt` on a shared volume, and PgBouncer reads them.

That does not survive a cluster. Pods are ephemeral, `ReadWriteMany` volumes
are rare, and the single-writer assumption breaks the moment you scale the
manager past one replica. So in Kubernetes the source of truth moves up to the
Kubernetes API:

```
  PgBouncerDatabase ──┐
  PgBouncerDatabase ──┼──▶ operator ──▶ Secret ──▶ PgBouncer pods
  PgBouncerPooler   ──┘                (3 files)      ▲
       ▲                                              │ SIGHUP from the
       │ you edit these                               │ reload sidecar
```

The domain logic is unchanged and literally shared: the same SCRAM hashing, the
same connect-string format, the same capacity arithmetic the API exposes at
`/api/capacity`.

The consequence worth internalising: **the manager's write API is disabled in
this deployment** (`READ_ONLY=true`). A tenant added through the UI would be
reverted on the operator's next reconcile, so the API refuses it with a 409
instead of accepting an edit that will not survive.

## Install

```bash
helm install pgbouncer charts/pgbouncer-manager \
  --namespace data --create-namespace \
  --set pooler.image.tag=v1.24.1
```

See the [Helm chart reference](helm.md) for every value.

## Declaring databases

Two equivalent ways. Through the chart, which is the fast path for many:

```yaml
databaseDefaults:
  host: db-primary.internal
  port: 5432
  poolSize: 20
  poolMode: transaction

databases:
  - name: acme
    dbname: acme_production
    user: acme
    password:
      secretKeyRef: {name: acme-db, key: password}
  - name: globex
    dbname: globex_production
    user: globex
    poolSize: 40
    password:
      secretKeyRef: {name: globex-db}
```

`databaseDefaults` is merged into every entry, so a hundred tenants on one
Postgres differ only in the fields that actually differ.

Or directly, which is what the chart produces:

```yaml
apiVersion: pgbouncer.adams-okode.github.io/v1alpha1
kind: PgBouncerDatabase
metadata:
  name: acme
  namespace: data
spec:
  host: db-primary.internal
  dbname: acme_production
  user: acme
  poolSize: 20
  password:
    secretKeyRef:
      name: acme-db
      key: password
```

Create the credential first:

```bash
kubectl -n data create secret generic acme-db --from-literal=password='...'
```

**Only `secretKeyRef` is accepted.** An inline password would sit in a custom
resource, which — unlike a Secret — is not covered by the encryption-at-rest
defaults or the RBAC most clusters put around secret reads.

## Watching it work

```bash
kubectl -n data get pgbouncerpoolers
kubectl -n data get pgbouncerdatabases
```

```
NAME       REPLICAS   DATABASES   READY   CAPACITY       AGE
pgbouncer  2          12          True    WithinBudget   4m
```

A database that did not make it into the config says why:

```bash
kubectl -n data get pgbouncerdatabase acme -o jsonpath='{.status.message}'
```

The pooler's status carries the same connection budget the API reports:

```bash
kubectl -n data get pgbouncerpooler pgbouncer -o jsonpath='{.status.targets}' | jq
```

```json
[{"host": "db-primary.internal", "port": 5432, "declaredTotal": 260,
  "maxConnections": 200, "headroom": -63, "status": "oversubscribed",
  "unboundedPools": []}]
```

and any warnings the operator wants you to see:

```bash
kubectl -n data get pgbouncerpooler pgbouncer -o jsonpath='{.status.warnings}' | jq
```

## How a config change reaches PgBouncer

Default is `reload.strategy: sighup`. The operator writes the Secret; the
kubelet refreshes the mounted files; a small sidecar in the pooler pod notices
and sends `SIGHUP` to PgBouncer, which re-reads its config **without dropping
established client connections**. On a pooler that matters: adding tenant 101
should not disconnect the other hundred.

The sidecar signals across containers, which needs `shareProcessNamespace: true`
on the pod. Both containers run as the same uid, so nothing beyond "signal your
own processes" is required. If your policy forbids a shared process namespace,
set `reload.strategy: rollout` — the pods then restart on every config change,
and every pooled session is interrupted.

Because the kubelet refreshes a Secret volume on its own sync period, a change
takes effect within roughly a minute rather than instantly.

## Rotating a password

Update the Secret. Nothing else:

```bash
kubectl -n data create secret generic acme-db \
  --from-literal=password='new' --dry-run=client -o yaml | kubectl apply -f -
```

The operator has `get` on Secrets but deliberately **not** `list` or `watch`,
so it cannot be notified and picks the change up on its resync interval
(`operator.resyncSeconds`, 120s by default). That is a deliberate trade: a
slower rotation in exchange for an operator token that cannot enumerate every
secret in the cluster if it leaks.

## Bring your own PgBouncer

Set `manageDeployment: false` and the operator renders only the config Secret,
leaving the Deployment to you. Mount the Secret at `/etc/pgbouncer` — as a
directory, never with `subPath`, which the kubelet never refreshes — and watch
`status.configChecksum` to know when to reload.

## What the operator does not do

- **It does not create databases or roles in Postgres.** It configures routing
  and pooling for databases and users that already exist.
- **It does not run more than one replica.** It is the only writer of the config
  Secret, so the chart pins it to one and uses a `Recreate` strategy.
- **It does not verify your PgBouncer image.** It overrides the entrypoint and
  runs `pgbouncer /etc/pgbouncer/pgbouncer.ini`, so any image carrying the
  binary works — pin a tag you have vetted.

## Security defaults

Every pod the operator creates runs unprivileged: non-root, read-only root
filesystem, all capabilities dropped, `allowPrivilegeEscalation: false`,
`seccompProfile: RuntimeDefault`. The pooler pod gets no service-account token,
because PgBouncer never calls the Kubernetes API.

Three things are **not** on by default and are worth turning on:

- `pooler.tls.enabled` — without it the client-to-pooler leg, including the
  SCRAM exchange, crosses the network in the clear.
- `networkPolicy.enabled` — a pooler holds credentials for every database
  behind it, so restricting who may open a socket to it is worthwhile.
- `pooler.settings.server_tls_sslmode` — set to `require` in the chart's
  defaults; raise it to `verify-full` with a CA once you have one.

See [Security](../security.md) for the rest.
