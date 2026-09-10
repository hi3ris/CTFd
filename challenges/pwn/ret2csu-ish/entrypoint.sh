#!/bin/sh
# Container entrypoint for ret2csu-ish.
#
# 1. Derive this team's flag from the injected TEAM_SECRET (see flag.py). The
#    flag is NEVER baked into the binary; it exists only in the live service:
#      - exported as FLAG in the served process's environment, and
#      - written to /tmp/flag.txt (tmpfs, runtime-only, NOT a downloadable
#        artifact) so a shell survives even an execve that clears envp.
#    Either way the flag is reachable ONLY by executing code in the process.
#    No arbitrary code execution -> no flag.
# 2. Serve one fresh `chall` process per TCP connection via socat. Each child
#    gets its own randomised landing key, so a hard-coded chain is worthless.
set -eu

FLAG="$(python3 /app/flag.py)"
export FLAG

# Runtime-only copy so a shell obtained via ROP can read it regardless of how
# execve was invoked. /tmp is a writable tmpfs; nothing is persisted or shipped.
umask 022
printf '%s\n' "$FLAG" > /tmp/flag.txt 2>/dev/null || true

PORT="${PORT:-9111}"
echo "[*] ret2csu-ish listening on 0.0.0.0:${PORT}" >&2

# fork: one child per connection. reuseaddr: fast restarts.
# The child (and any process it execve's) inherits FLAG from this environment.
exec socat -T120 \
    TCP-LISTEN:"${PORT}",reuseaddr,fork \
    EXEC:"/app/chall",stderr
