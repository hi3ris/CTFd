#!/bin/sh
# Entrypoint for a boot2root KotH hill (shared SSH box). Runs as root: sets the
# player password, (re)creates the two king files with the right ownership,
# generates host keys, starts the scorer (root, exposes /king), then execs
# sshd. SCORER_SECRET must match CTFd's KOTH_SCORER_SECRET (or the hill's
# per-hill scorer_secret).
set -eu
: "${SCORER_SECRET:?SCORER_SECRET must be set (must match CTFd KOTH_SCORER_SECRET)}"

printf 'player:%s\n' "${B2R_SSH_PASSWORD:-player}" | chpasswd
ssh-keygen -A >/dev/null 2>&1

# Root king: only root may plant a token here (full points).
: > /root/king.txt
chown root:root /root/king.txt
chmod 0600 /root/king.txt
chmod 0700 /root

# User king: the player may write it (half points). Kept fresh-writable across
# restarts so a user hold is always possible without root.
: > /home/player/king.txt
chown player:player /home/player/king.txt
chmod 0664 /home/player/king.txt

SCORER_PORT="${SCORER_PORT:-8082}" python3 /opt/scorer.py &
echo "[entrypoint] boot2root: scorer on ${SCORER_PORT:-8082}, sshd on 22 (login player)" >&2
exec /usr/sbin/sshd -D -e
