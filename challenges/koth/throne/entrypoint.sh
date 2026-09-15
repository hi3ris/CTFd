#!/bin/sh
# Entrypoint for the KotH hill "The Throne".
#
# HILL_KEY is the secret players must exploit out of the box; if not provided it
# is generated randomly at startup. SCORER_SECRET must match the CTFd plugin's
# KOTH_SCORER_SECRET so CTFd (and only CTFd) can read /king.
set -eu

if [ -z "${HILL_KEY:-}" ]; then
    HILL_KEY="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    export HILL_KEY
fi

: "${SCORER_SECRET:?SCORER_SECRET must be set (must match CTFd KOTH_SCORER_SECRET)}"

echo "[entrypoint] throne starting; HILL_KEY set (${#HILL_KEY} hex chars), skew=${SKEW:-45}s" >&2
exec python3 /opt/throne/app.py
