#!/bin/sh
# Entrypoint for the Citadel (shared SSH KotH). Runs as root: sets the player
# password, generates host keys, starts the scorer (root, exposes /king), then
# execs sshd. SCORER_SECRET must match CTFd's KOTH_SCORER_SECRET.
set -eu
: "${SCORER_SECRET:?SCORER_SECRET must be set (must match CTFd KOTH_SCORER_SECRET)}"

printf 'player:%s\n' "${CITADEL_SSH_PASSWORD:-player}" | chpasswd
ssh-keygen -A >/dev/null 2>&1

SCORER_PORT="${SCORER_PORT:-8081}" python3 /opt/scorer.py &
echo "[entrypoint] citadel: scorer on ${SCORER_PORT:-8081}, sshd on 22 (login player)" >&2
exec /usr/sbin/sshd -D -e
