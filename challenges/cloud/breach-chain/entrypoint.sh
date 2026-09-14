#!/bin/sh
# Entrypoint for cloud-breach-chain. Generates an internal APP_SECRET if none is
# provided (it only gates the internal metadata token, never the flag). FLAG /
# CHALLENGE_SECRET are injected per team by the instancier and read by flag.py.
set -eu
if [ -z "${APP_SECRET:-}" ]; then
    APP_SECRET="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    export APP_SECRET
fi
echo "[entrypoint] kekeli breach-chain: public app + internal IMDS starting" >&2
exec python3 /opt/app/app.py
