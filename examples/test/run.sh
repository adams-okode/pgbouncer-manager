#!/usr/bin/env bash
#
# End-to-end test for the example stack.
#
# Proves the full management loop against a real PgBouncer + Postgres:
#   1. add a tenant through the manager API
#   2. the credential is stored hashed (SCRAM), never plaintext
#   3. the manager reloads PgBouncer
#   4. a client routed THROUGH PgBouncer reaches the new tenant's database
#   5. the manager reports the live pool
#
# Usage:  examples/test/run.sh
set -euo pipefail

cd "$(dirname "$0")/.."   # -> examples/
COMPOSE="docker compose"

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
step()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

cleanup() { $COMPOSE down -v >/dev/null 2>&1 || true; }
trap cleanup EXIT

fail() { red "FAIL: $*"; $COMPOSE logs --no-color | tail -50; exit 1; }

step "Building and starting the stack"
$COMPOSE up -d --build

step "Waiting for the manager API"
for _ in $(seq 1 60); do
  curl -sf http://localhost:3000/api/health >/dev/null 2>&1 && break || sleep 1
done
curl -sf http://localhost:3000/api/health >/dev/null 2>&1 || fail "manager API never became healthy"
green "manager is up"

step "Adding tenant 't1' via the manager API"
curl -sf -X POST http://localhost:3000/api/tenants \
  -H 'Content-Type: application/json' \
  -d '{"id":"t1","host":"postgres","port":5432,"db_name":"tenantdb","user":"postgres","password":"tenantpass","pool_size":10}' \
  || fail "POST /api/tenants failed"
green "tenant added"

step "Asserting the credential is hashed (not plaintext) in userlist.txt"
userlist="$($COMPOSE exec -T manager cat /etc/pgbouncer/userlist.txt)"
echo "$userlist"
echo "$userlist" | grep -q 'SCRAM-SHA-256\$' || fail "no SCRAM-SHA-256 verifier found"
if echo "$userlist" | grep -q 'tenantpass'; then fail "plaintext password leaked into userlist.txt"; fi
green "credential stored as a SCRAM-SHA-256 verifier"

step "Reloading PgBouncer through the manager (admin-console RELOAD)"
curl -sf -X POST http://localhost:3000/api/pools/reload || fail "POST /api/pools/reload failed"
green "reload issued"

step "Connecting THROUGH PgBouncer to tenant 't1' and running a query"
routed=""
for _ in $(seq 1 20); do
  if $COMPOSE exec -T postgres \
       psql "host=pgbouncer port=6432 user=postgres dbname=t1" \
       -tAc "select 'routed_ok'" 2>/dev/null | grep -q routed_ok; then
    routed=1; break
  fi
  sleep 1
done
[ -n "$routed" ] || fail "could not query tenant 't1' through PgBouncer"
green "query routed through PgBouncer to the tenant database"

step "Pool status reported by the manager"
curl -sf http://localhost:3000/api/pools/status; echo

green "\nPASS — add → hash → reload → route → query all verified end-to-end."
