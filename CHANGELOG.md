# Changelog

## [2.1.1](https://github.com/adams-okode/pgbouncer-manager/compare/v2.1.0...v2.1.1) (2026-08-27)


### Documentation

* add CLAUDE.md with contribution and release conventions ([b34ba47](https://github.com/adams-okode/pgbouncer-manager/commit/b34ba47d08f5c7748810259478fef08871fbf5d4))
* record that DOCKERHUB_TOKEN needs delete scope ([c621b5e](https://github.com/adams-okode/pgbouncer-manager/commit/c621b5e52d80e8af7a64be83272334206e4dc0f9))
* require branch + pull request for all changes ([140de52](https://github.com/adams-okode/pgbouncer-manager/commit/140de523bfe7504314185584d9d3b2525054b4de))
* require branch + pull request for all changes ([21d979d](https://github.com/adams-okode/pgbouncer-manager/commit/21d979d466bf3c68761c7420fb27359d8295d7e5))

## [2.1.0](https://github.com/adams-okode/pgbouncer-manager/compare/v2.0.0...v2.1.0) (2026-08-27)


### ⚠ BREAKING CHANGES

* API paths move from /tenants and /pools to /api/tenants and /api/pools, and the health check from / to /api/health.

### Features

* **capacity:** report committed connections per target Postgres ([4228e93](https://github.com/adams-okode/pgbouncer-manager/commit/4228e9316e931cb41806c994ac36d7f202367283))
* **cli:** make the CLI a real thin HTTP client of the API ([e6f517d](https://github.com/adams-okode/pgbouncer-manager/commit/e6f517d1b11a0898886bf2489f2b94b121d0b516))
* **config:** add pydantic-settings config and PgBouncer credential hashing ([2d8c6fc](https://github.com/adams-okode/pgbouncer-manager/commit/2d8c6fc8801c71df68c2710dde52660dcca5cd63))
* serve the bundled web UI from the backend ([ec5a44c](https://github.com/adams-okode/pgbouncer-manager/commit/ec5a44c093cf99a1141cd480ffa7a52c9230d127))
* **service:** introduce PgBouncer service layer ([e4f5e20](https://github.com/adams-okode/pgbouncer-manager/commit/e4f5e20a177a01984a97ec45c1d80837a6b06fa3))
* **ui:** rebuild the interface on Radix Themes ([d5d3b3b](https://github.com/adams-okode/pgbouncer-manager/commit/d5d3b3b7a6441822311622390605262829924db3))
* **ui:** wire the frontend to the real API ([94870a6](https://github.com/adams-okode/pgbouncer-manager/commit/94870a6ab01773340d8b2db08d0600a4670fd88c))


### Bug Fixes

* **ci:** make ruff reproducible and stop B008 false positives ([e59d873](https://github.com/adams-okode/pgbouncer-manager/commit/e59d8735c0de370d85e8e920d7004e94e7ee3e3e))
* **service:** write config files readable by a non-root PgBouncer ([fb78e2a](https://github.com/adams-okode/pgbouncer-manager/commit/fb78e2ade438d6e2f15759a6b9d3db347c788982))


### Refactoring

* **api:** rewrite tenant/pool routes on the service layer ([604bce5](https://github.com/adams-okode/pgbouncer-manager/commit/604bce56f6c3c2b9be74c3340788f90fc9ced78a))


### Documentation

* align docs with reality and de-boilerplate the README ([7b5cdc9](https://github.com/adams-okode/pgbouncer-manager/commit/7b5cdc98d23a69ccb311aaab0d1d6e7adb738cf4))
* document the /api move, capacity endpoint, and bundled UI ([4ccc9ca](https://github.com/adams-okode/pgbouncer-manager/commit/4ccc9caf53c6e4c463182a8ef0d194ca65cfca18))
* **example:** add docker compose stack + end-to-end test ([0ef2592](https://github.com/adams-okode/pgbouncer-manager/commit/0ef2592336af66805a2aa3c43d253c93ea5b05f2))
* update documantation to make it more readable ([29e68f5](https://github.com/adams-okode/pgbouncer-manager/commit/29e68f5e2bb101eb224118f85d388d01b2987f17))
* update README for clarity and structure improvements ([4a737b9](https://github.com/adams-okode/pgbouncer-manager/commit/4a737b965e223afffa2f101cab379d8ef5267cdd))


### Chores

* derive versions from commits and publish to Docker Hub on release ([3e153b6](https://github.com/adams-okode/pgbouncer-manager/commit/3e153b63b629a9c5276426c1b266a6c0a94a67ac))
