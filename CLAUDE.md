# Contributing to pgbouncer-manager

Read this before changing anything. It covers the conventions that are not
recoverable by reading the code.

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
pytest                   # unit + API tests
ruff check .             # lint
mypy app cli             # type check
cd ui && npm run build   # type-checks the SPA as well as building it
```

CI runs exactly these. `ruff` and `mypy` are not advisory — a violation
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

## Scope discipline

Do only what was asked. Do not opportunistically delete "dead" files, reformat
untouched code, or add comments/types to code you did not change. If you spot
something unrelated that is genuinely broken, say so and let the user decide
rather than folding it into the current change.
