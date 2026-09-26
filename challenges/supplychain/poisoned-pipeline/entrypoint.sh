#!/bin/sh
# Entrypoint for supplychain-poisoned-pipeline. FLAG / CHALLENGE_SECRET are
# injected per team by the instancier; minici.py reads the flag then scrubs those
# env vars so no build step can recover it from the runner's environ.
set -eu
echo "[entrypoint] MiniCI runner starting" >&2
exec python3 /opt/ci/minici.py
