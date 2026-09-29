#!/bin/sh
# /usr/local/sbin/rotate-hook.sh
# Runs as root (from logrotate postrotate, or via sudo). Derives a rotation
# token from the config and drops it in the secrets dir under a derived name.
set -eu

. /etc/app/rotate.conf

# Derived token filename: app-<CYCLE>-<HOSTID>.token
NAME="app-${CYCLE}-${HOSTID}.token"
OUT="${SECRET_DIR}/${NAME}"

# Derived token value: first 10 hex chars of sha256(CYCLE:HOSTID:ROTATE_SECRET).
# Deterministic, so it is fully reconstructable from rotate.conf.
TOKEN=$(printf '%s:%s:%s' "$CYCLE" "$HOSTID" "$ROTATE_SECRET" \
    | sha256sum | cut -c1-10)

install -d -m 0700 "$SECRET_DIR"
umask 077
printf '%s\n' "$TOKEN" > "$OUT"
