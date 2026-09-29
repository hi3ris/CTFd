#!/bin/sh
# Entrypoint for the KotH hill "Réseau Fortune".
#
# SCORER_SECRET must match the CTFd plugin's KOTH_SCORER_SECRET so CTFd (and only
# CTFd) can read /king. State is in-memory: restarting resets the economy.
set -eu

: "${SCORER_SECRET:?SCORER_SECRET must be set (must match CTFd KOTH_SCORER_SECRET)}"

echo "[entrypoint] reseau-fortune starting on :${PORT:-8080}" >&2
exec python3 /opt/reseau/app.py
