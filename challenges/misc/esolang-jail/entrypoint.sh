#!/bin/sh
# Container entrypoint for misc-esolang-jail.
#
# 1. Resolve this instance's flag via flag.py, which reads the per-challenge
#    contract: FLAG if injected, else CHALLENGE_SECRET[:24] (see flag.py). The
#    flag is NEVER baked into the image or any handout. It exists only:
#      - in the environment of the interpreter process socat spawns (so it is
#        visible via /proc/self/environ or an env lookup), and
#      - in a file at /flag/flag.txt (mode 0644 on a tmpfs),
#    both of which are reachable ONLY once the player escapes the Marble jail.
#    A benign program cannot read either one.
# 2. Serve one fresh interpreter (a stateful REPL) per TCP connection via socat.
set -eu

FLAG="$(python3 /app/flag.py)"
export FLAG

# Secondary location for the same flag: a plain file. Reachable only via the
# escape's file-read primitive. /flag is a tmpfs so this works on a read-only
# root filesystem (see docker-compose.yml).
mkdir -p /flag 2>/dev/null || true
if printf '%s\n' "$FLAG" > /flag/flag.txt 2>/dev/null; then
    chmod 0644 /flag/flag.txt 2>/dev/null || true
fi

PORT="${PORT:-9301}"
echo "[*] esolang-jail (Marble) listening on 0.0.0.0:${PORT}" >&2

# fork: one child per connection. reuseaddr: fast restarts. Each child inherits
# FLAG from this shell's environment; socat wires the TCP socket to the child's
# stdin/stdout so the REPL is fully interactive.
exec socat -T120 \
    TCP-LISTEN:"${PORT}",reuseaddr,fork \
    EXEC:"python3 /app/interp.py",stderr
