#!/bin/sh
# Boot the pwn-relaybox-canary service. Runs briefly as root to write this instance's flag,
# then drops to the unprivileged app user to serve HTTP.
set -e

python3 -c 'from flag import get_flag; print(get_flag())' > /flag.txt
chmod 0644 /flag.txt

exec su-exec appuser python3 /app/app.py
