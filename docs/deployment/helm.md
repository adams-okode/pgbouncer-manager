# Helm chart

The chart in `charts/pgbouncer-manager` installs the operator, its CRDs and
RBAC, a `PgBouncerPooler`, the `PgBouncerDatabase` resources you declare, and
optionally the read-only management UI.

```bash
helm install pgbouncer charts/pgbouncer-manager \
  --namespace data --create-namespace \
  -f my-values.yaml
```

## A complete example

```yaml
pooler:
  image:
    repository: edoburu/pgbouncer
    tag: "v1.24.1"
  replicas: 3
  tls:
    enabled: true
    secretName: pgbouncer-tls
  capacityLimits:
    db-primary.internal:5432: 200
  settings:
    max_client_conn: 2000
    default_pool_size: 25
    server_tls_sslmode: verify-full
    server_tls_ca_file: /etc/pgbouncer/tls/ca.crt

databaseDefaults:
  host: db-primary.internal
  port: 5432
  poolSize: 20
  poolMode: transaction

databases:
  - name: acme
    dbname: acme_production
    user: acme
    password: {secretKeyRef: {name: acme-db}}
  - name: globex
    dbname: globex_production
    user: globex
    poolSize: 40
    password: {secretKeyRef: {name: globex-db}}

networkPolicy:
  enabled: true
  allowFrom:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: apps
```

Adding a tenant later is an edit to `databases` and a `helm upgrade`. PgBouncer
reloads in place; the other tenants' connections are untouched.

## Values

### Operator

| Key | Default | What it does |
|---|---|---|
| `operator.enabled` | `true` | Install the operator. |
| `operator.image.repository` | `adamsokode/pgbouncer-manager` | Operator, reload sidecar and manager are one image. |
| `operator.image.tag` | `""` | Defaults to the chart's `appVersion`. |
| `operator.watchNamespace` | `""` | Empty watches the cluster (ClusterRole). A namespace narrows RBAC to a Role. |
| `operator.resyncSeconds` | `120` | How often to re-render without an event. This is what picks up a rotated password Secret. |
| `operator.replicas` | `1` | Leave at 1. The operator is the only writer of the config Secret. |
| `operator.rbac.create` | `true` | Create the Role/ClusterRole and binding. |

### Pooler

| Key | Default | What it does |
|---|---|---|
| `pooler.enabled` | `true` | Create a `PgBouncerPooler`. |
| `pooler.image.repository` | `edoburu/pgbouncer` | Any image with the `pgbouncer` binary; the entrypoint is overridden. **Pin a tag you have vetted.** |
| `pooler.replicas` | `2` | A PodDisruptionBudget is created at 2 or more. |
| `pooler.authType` | `scram-sha-256` | Client auth. `trust`/`any` accept anyone and are reported as a warning. |
| `pooler.authScheme` | `scram-sha-256` | Hash format in `userlist.txt`. Changing it re-hashes every credential. |
| `pooler.adminPasswordSecret.name` | `""` | Needed only when `manager.enabled` — the admin console needs a credential from off-pod. |
| `pooler.settings` | see values | Extra `[pgbouncer]` options. Operator-managed keys are rejected. |
| `pooler.tls.enabled` | `false` | Client-facing TLS. **Turn this on.** |
| `pooler.reload.strategy` | `sighup` | `sighup` keeps connections; `rollout` restarts pods. |
| `pooler.capacityLimits` | `{}` | `max_connections` per `host:port`. Without it capacity reports `unknown`. |
| `pooler.security.runAsUser` | `1100` | Change if your PgBouncer image needs a different uid. |

### Databases

| Key | Default | What it does |
|---|---|---|
| `databaseDefaults` | `{}` | Merged into every entry in `databases`. |
| `databases` | `[]` | One `PgBouncerDatabase` per entry. |

Each entry takes the `PgBouncerDatabase` spec fields: `name`, `dbname`, `user`,
`password.secretKeyRef`, `poolSize`, `poolMode`, `reservePoolSize`,
`maxDbConnections`, `options`.

### Manager UI

| Key | Default | What it does |
|---|---|---|
| `manager.enabled` | `false` | Deploy the read-only UI and API. |
| `manager.serveUI` | `true` | Serve the SPA as well as the API. |
| `manager.ingress.enabled` | `false` | The UI ships **no authentication**. Only expose it behind something that does. |

The manager runs with `READ_ONLY=true`: the custom resources own the config, so
writes are refused rather than silently reverted on the next reconcile.

### Network policy

| Key | Default | What it does |
|---|---|---|
| `networkPolicy.enabled` | `false` | Default-deny ingress to the pooler. |
| `networkPolicy.allowFrom` | `[]` | Peers allowed to reach the pooler port. An empty list is a closed door. |

## CRDs

CRDs are templated (not in `crds/`) so `helm upgrade` actually updates them —
Helm never upgrades the `crds/` directory. They carry
`helm.sh/resource-policy: keep`, so `helm uninstall` leaves your
`PgBouncerDatabase` resources alone rather than cascade-deleting your entire
tenant list.

Set `crds.install=false` if something else manages them.

## Upgrading

```bash
helm upgrade pgbouncer charts/pgbouncer-manager -f my-values.yaml
```

The chart's `version` and `appVersion` are owned by release-please and move
together with the application. Pinning the chart pins the image.
