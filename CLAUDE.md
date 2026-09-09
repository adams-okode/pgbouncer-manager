# Contributing to pgbouncer-manager

Read this before changing anything. It covers the conventions that are not
recoverable by reading the code.

## Never push to `main`

All work goes on a branch and through a pull request. Branch **before** the
first commit, open the PR, and stop — the repository owner merges it.

This is not ceremony. `main` is what release-please cuts releases from, and
tags are published off that history. Once a release exists, moving commits that
are already on `main` means a force-push that orphans the released tag's
ancestry, so "I'll tidy it into a PR afterwards" is not available as a fallback.

The single exception is release-please's own `chore(main): release X.Y.Z` PR,
which has to land on `main` to cut the release. The owner merges that too.

## Commit messages are load-bearing

Versioning is fully automated by release-please. **The commit message decides
the next version number**, so a sloppy prefix ships a wrong release.

| Prefix | Effect |
|--------|--------|
| `fix:` | patch bump |
| `feat:` | minor bump |
| `feat!:` or a `BREAKING CHANGE:` footer | major bump |
| `docs:` `chore:` `ci:` `build:` `test:` `refactor:` `perf:` | no bump on their own |

Rules:

- Use a scope when the change is localised: `fix(service):`, `feat(ui):`.
- Never hand-edit a version in `pyproject.toml`, `ui/package.json`, or
  `CHANGELOG.md`. release-please owns all three; editing them causes conflicts
  in the release PR.
- Never create a `v*` tag by hand.
- To force a specific version, add a `Release-As: X.Y.Z` footer to any commit
  landing in that release.
- Subject line: imperative mood, no trailing period, keep it under ~72 chars.
  Explain *why* in the body, not *what* — the diff already says what.

## Releasing

Push to `main` → release-please opens/updates a `chore(main): release X.Y.Z`
PR. **Merging that PR is the release.** It tags `vX.Y.Z`, publishes the GitHub
Release, and — in the same workflow run — pushes the multi-arch image to
Docker Hub as `:X.Y.Z`, `:X.Y`, and `:latest`.

Two non-obvious constraints, both already handled in config; do not "simplify"
them away:

- `build.yml` is invoked via `workflow_call` from `release.yml`, **not** by a
  `release: published` event. Tags and releases created with the default
  `GITHUB_TOKEN` do not trigger other workflows, so an event-driven chain
  silently never fires. This is why the image had never been published before.
- A called workflow still sees the *caller's* ref, so `build.yml` takes the tag
  as an explicit input and passes it to `docker/metadata-action` as
  `type=semver,...,value=${{ inputs.ref }}`. Without it no semver tag is
  produced — and metadata-action *skips* unparseable tags rather than failing,
  so the breakage is silent. For the same reason
  `include-component-in-tag: false` must stay set, or tags become
  `pgbouncer-manager-v2.1.0` and stop parsing.

Requires repo secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`, and the
repo setting *Allow GitHub Actions to create and approve pull requests*.

`DOCKERHUB_TOKEN` must have **read/write/delete** scope. Pushing an image only
needs read/write, but `dockerhub-description.yml` also uses this token to
update the repository overview, and that endpoint rejects a read/write-only
token — it authenticates successfully and then returns a bare `Forbidden`.

## Docker Hub overview

`.github/DOCKERHUB.md` is the repository overview shown on Docker Hub, synced
by `dockerhub-description.yml` on push to `main`. It is intentionally *not*
`README.md`: the README targets contributors, this targets someone deploying
the image. It also lives outside `docs/` so MkDocs does not publish it as an
orphan page competing with the real deployment docs in search.

Keep the version numbers in its Tags table current when they drift.

## Checks to run before committing

```bash
pytest                            # unit + API tests
ruff check .                      # lint
mypy app cli controller           # type check
helm lint charts/pgbouncer-manager
cd ui && npm run build            # type-checks the SPA as well as building it
```

CI runs exactly these. `tests/test_chart.py` skips itself when `helm` is not
installed, so a green `pytest` without helm does not mean the chart is fine. `ruff` and `mypy` are not advisory — a violation
anywhere in the tree fails the build, including in files you did not touch.

## Domain gotchas

- **Pool sizes add up.** A PgBouncer pool is keyed on the `databases.ini` entry
  name plus the forced user, *not* the target dbname. Several tenants pointing
  at the same Postgres each get their own pool, so `pool_size` values sum
  against that server's `max_connections`. This is what `/api/capacity`
  computes.
- **An entry with no `user=` is unbounded.** PgBouncer opens one pool *per
  connecting user*, so the real connection count can exceed anything the
  capacity math shows. The UI flags these.
- **Credentials are never stored in plaintext.** Passwords become
  PgBouncer-compatible SCRAM-SHA-256 (or md5) hashes before touching disk.
  Do not add a code path that writes or logs a raw password.
- **The files are the state.** Config writes are atomic and assume a single
  writer; two manager instances on a shared volume will race.
- **`GET /` is not a health check.** The SPA is mounted at `/` as a catch-all
  and answers unconditionally, even with a dead API. Probes must use
  `/api/health`.

## Frontend

- Radix Themes (`@radix-ui/themes`), no Tailwind. Do not reintroduce a utility
  CSS framework — its preflight reset conflicts with Radix's.
- `ui/src/index.css` imports Radix tokens **granularly** (base + only the
  palettes actually used) rather than the bundled `styles.css`, which cut the
  CSS by ~27%. If you use a new accent colour, add its token file there.
- Prefer Radix components over hand-rolled ones — `AlertDialog` instead of
  `window.confirm`, `Dialog` for forms, `Tabs` for navigation.

## Kubernetes operator and Helm chart

The operator lives in `controller/`, **not** `operator/`. `operator` is a
standard-library module name; a top-level package with that name shadows it for
the whole process and breaks any dependency that imports it.

- **One image, three roles.** The published image runs the API/UI, the operator
  (`python -m controller`), and the reload sidecar (`python -m
  controller.reloader`). That is why `requirements-operator.txt` is installed
  into it even though `pip install pgbouncer-manager` does not pull those deps
  (they are the `[operator]` extra). Do not split it into a second image without
  also reworking `build.yml`, which publishes exactly one.
- **`controller/reconcile.py` and `controller/objects.py` are pure.** They take
  resolved inputs and return file content or plain dicts. Keep cluster I/O in
  `handlers.py`/`kube.py` — the tests depend on the split.
- **Never re-hash a credential that already matches.** SCRAM verifiers are
  randomly salted, so re-hashing an unchanged password produces different bytes
  every pass, and every pass then looks like a change and reloads PgBouncer.
  `auth.verify_password` exists for this; `_matches_scheme` exists so that
  changing `authScheme` still forces a genuine re-hash.
- **The chart's `version` and `appVersion` are release-please's**, listed in
  `release-please-config.json` `extra-files` alongside `ui/package.json`. Same
  rule as the others: never hand-edit them.
- **CRDs are templated, not in `crds/`.** Helm never upgrades the `crds/`
  directory, so a schema change would silently not apply. They carry
  `helm.sh/resource-policy: keep` so `helm uninstall` does not cascade-delete
  every `PgBouncerDatabase` in the cluster.
- **`tests/test_chart.py` is the only thing connecting the chart to the
  operator.** It renders the chart and parses the result with the operator's own
  models. A values key renamed on one side and not the other fails there and
  nowhere else.
- **`spec.settings` must keep rejecting reserved ini keys.** Accepting
  `auth_type` or `auth_file` from a free-form map lets anyone who can edit a
  pooler turn off authentication for every database behind it.

## Scope discipline

Do only what was asked. Do not opportunistically delete "dead" files, reformat
untouched code, or add comments/types to code you did not change. If you spot
something unrelated that is genuinely broken, say so and let the user decide
rather than folding it into the current change.
