#!/bin/sh
# /usr/local/sbin/rotate-hook.sh
# Runs as root (from logrotate postrotate, or via sudo). Mints a rotation token
# and drops it in the secrets dir under a name derived from the config.
set -eu

. /etc/app/rotate.conf

# Derived token filename: app-<CYCLE>-<HOSTID>.token
NAME="app-${CYCLE}-${HOSTID}.token"
OUT="${SECRET_DIR}/${NAME}"

# Freshly minted per rotation (random). The shipped host snapshot captured the
# most recent value in the file below.
ROTATION_TOKEN="$(openssl rand -hex 5)"

install -d -m 0700 "$SECRET_DIR"
umask 077
printf '%s\n' "$ROTATION_TOKEN" > "$OUT"
