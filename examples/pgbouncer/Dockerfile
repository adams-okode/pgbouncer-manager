# Minimal, file-driven PgBouncer. It reads the config the manager writes into
# the shared /etc/pgbouncer volume. Runs in the foreground.
#
# PgBouncer refuses to run as root and the package ships no service user, so we
# create one. The manager writes config files world-readable (0644), so this
# non-root user can read them after every rewrite/RELOAD.
FROM alpine:3.20

RUN apk add --no-cache pgbouncer postgresql-client \
    && adduser -D -u 1100 pgb

EXPOSE 6432
USER pgb

CMD ["pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]
