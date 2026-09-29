#!/bin/sh
# heap-note service entrypoint.
#
# Resolves THIS instance's flag via flag.py (which reads the injected FLAG /
# CHALLENGE_SECRET -- see flag.py), exports it as FLAG, and serves one fresh
# process of ./chall per TCP connection via socat. The flag is never written to
# disk and is only reachable by hijacking control flow into win(), which reads
# getenv("FLAG").
set -eu

PORT="${PORT:-9022}"

# Derive the per-team flag into the environment. Every connection's child
# process inherits it (socat passes the environment through to the exec'd
# program). win() prints it; nothing else does.
FLAG="$(python3 /chall/flag.py)"
export FLAG

echo "[entrypoint] heap-note listening on 0.0.0.0:${PORT}"

# One process per connection; hard wall-clock cap so a stuck client cannot pin a
# worker forever. reuseaddr for quick restarts. No pty: the exploit sends raw
# 8-byte addresses via read(2), so the socket must be a byte-transparent pipe
# (a pty line discipline would mangle CR/LF and control bytes). stderr is merged
# into the socket so a crash is visible while solving.
exec socat -T120 \
    TCP-LISTEN:"${PORT}",reuseaddr,fork \
    EXEC:"/chall/chall",stderr
