#!/bin/sh
# ModelHub (ml-pickle-rce) service entrypoint.
#
# Resolves THIS instance's flag via flag.py (from the injected FLAG /
# CHALLENGE_SECRET; see flag.py) and writes it to the flag file on the service
# host. The flag never appears in any response unless a solver executes code
# during unpickling and reads the file back out.
set -eu

PORT="${PORT:-9080}"
FLAG_PATH="${FLAG_PATH:-/flag}"
export FLAG_PATH

# Write the per-team flag to the host filesystem, world-readable so the exploit
# (running as the same unprivileged service user) can read it. It is a plain
# file with nothing else in it.
python3 /app/flag.py > "$FLAG_PATH"
chmod 0644 "$FLAG_PATH"

# One decoy: a stale placeholder that is obviously not a flag. Refutable in
# seconds by reading it. Never the real flag; costs no attempt to rule out.
printf '%s\n' 'CTF{not_the_flag_this_is_an_old_test_fixture_ignore}' > /flag.decoy
chmod 0644 /flag.decoy

echo "[entrypoint] ModelHub listening on 0.0.0.0:${PORT} (flag at ${FLAG_PATH})"

# gunicorn: a couple of threaded workers, short request timeout. The service is
# tiny and stateless.
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --threads 4 \
    --timeout 30 \
    --access-logfile - \
    app:app
