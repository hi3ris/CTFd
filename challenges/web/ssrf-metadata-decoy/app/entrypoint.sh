#!/bin/sh
# Runs as root ONLY to set up the link-local network alias, then drops to the
# unprivileged 'appuser' to run the services. The application never runs as root.
set -e

# Add the canonical cloud-metadata link-local address to loopback so the decoy
# can bind 169.254.169.254:80. Needs NET_ADMIN; if unavailable, run.py falls
# back to 127.0.0.254 and prints a warning.
if ip addr add 169.254.169.254/32 dev lo 2>/dev/null; then
    echo "[entrypoint] added 169.254.169.254/32 to lo"
else
    echo "[entrypoint] could not add link-local alias (need NET_ADMIN); decoy will use fallback addr"
fi

exec su-exec appuser python3 /app/run.py
