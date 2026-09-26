#!/bin/sh
# Entrypoint for boot2root-ssh. Runs as root: generates host keys, plants the
# root-only flag, sets the ctf login password, scrubs secrets, then hands off to
# sshd. The player enters as `ctf` and must privesc to root to read /root/flag.
set -eu

# 1. flag -> /root/flag (root:root 400), never in the image.
FLAG="$(python3 /opt/flag.py)"
printf '%s\n' "$FLAG" > /root/flag
chown root:root /root/flag
chmod 400 /root/flag

# 2. ctf login password (given to the player). CTF_SSH_PASSWORD overridable.
printf 'ctf:%s\n' "${CTF_SSH_PASSWORD:-ctf}" | chpasswd

# 3. host keys + scrub flag-bearing env so no shell inherits it.
ssh-keygen -A >/dev/null 2>&1
unset FLAG CHALLENGE_SECRET TEAM_SECRET CTF_SSH_PASSWORD

echo "[entrypoint] boot2root-ssh: flag planted (root:root 400); sshd on 22 (login ctf)" >&2
exec /usr/sbin/sshd -D -e
