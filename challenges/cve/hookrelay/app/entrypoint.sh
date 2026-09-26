#!/bin/sh
# Boot the Hookrelay mirror agent.
#
# Runs briefly as root to (1) materialise this instance's flag into a file that
# only the exploited command can read, and (2) enable the ext transport that the
# internal mirror workflow relies on -- the misconfiguration the challenge turns
# on. Then drops to the unprivileged 'appuser' to serve HTTP.
set -e

FLAG_FILE=/flag.txt

# Write the per-team flag (FLAG / CHALLENGE_SECRET injected by the instancier;
# LOCAL DEV fallback otherwise). Never served by any route.
python3 -c 'from flag import get_flag; print(get_flag())' > "$FLAG_FILE"
chmod 0644 "$FLAG_FILE"

# Scratch dir served read-only under /pub/. Owned by the app user so a command
# run via the CVE (which runs as appuser) can drop a file here to read it back.
mkdir -p /app/pub
chown appuser /app/pub
chmod 0755 /app/pub

# The mirror agent legitimately clones over ext:: from internal transports, so
# the operators enabled it globally. This is the door CVE-2022-24439 walks
# through: with GitPython 3.1.29 not validating the URL, ext:: runs a command.
git config --global protocol.ext.allow always
git config --system protocol.ext.allow always 2>/dev/null || true
# Make the same config visible to the unprivileged user that serves HTTP.
su-exec appuser git config --global protocol.ext.allow always

exec su-exec appuser python3 /app/app.py
