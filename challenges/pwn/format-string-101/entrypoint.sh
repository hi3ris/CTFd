#!/bin/sh
# Container entrypoint for format-string-101.
#
# 1. Derive this team's flag from the injected TEAM_SECRET (see flag.py). The
#    flag is NEVER baked into the binary; it only exists in the environment of
#    the per-connection child process that socat spawns, and the binary reveals
#    it only after it has verified the effect (auth == this connection's nonce).
# 2. Serve one fresh `chall` process per TCP connection via socat. Each child
#    gets its own randomised nonce, so a replayed payload is worthless.
set -eu

FLAG="$(python3 /app/flag.py)"
export FLAG

PORT="${PORT:-9101}"
echo "[*] format-string-101 listening on 0.0.0.0:${PORT}" >&2

# fork: one child per connection.  reuseaddr: fast restarts.
# The child inherits FLAG from this shell's environment.
exec socat -T60 \
    TCP-LISTEN:"${PORT}",reuseaddr,fork \
    EXEC:"/app/chall",stderr
