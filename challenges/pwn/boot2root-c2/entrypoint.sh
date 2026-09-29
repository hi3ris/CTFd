#!/bin/sh
# Container entrypoint for boot2root-c2 (Phantom Wire staging server).
#
# Runs as ROOT at startup so it can plant the flag where only root can read it,
# then permanently drops to the unprivileged `www` user to serve the foothold.
#
# 1. Derive THIS instance's flag via flag.py (reads injected FLAG /
#    CHALLENGE_SECRET). The flag is never baked into the image.
# 2. Write it to /root/flag, mode 400, owned by root:root -- the ONLY copy on
#    the box, not world-readable. Reading it as root IS the win condition.
# 3. Scrub every flag-bearing secret from the environment, then drop to `www`
#    and exec the network-facing panel. From that unprivileged shell the player
#    must climb the local privesc chain (SUID config -> sudo module-hijack).
set -eu

FLAG="$(python3 /opt/flag.py)"
printf '%s\n' "$FLAG" > /root/flag
chown root:root /root/flag
chmod 400 /root/flag

# The foothold runs as www and must NOT inherit CHALLENGE_SECRET / TEAM_SECRET:
# flag == NCTF{CHALLENGE_SECRET[:24]}, so a www shell that could read `env`
# would otherwise recover the flag with zero privesc.
unset FLAG CHALLENGE_SECRET TEAM_SECRET

PORT="${PORT:-8080}"
echo "[entrypoint] boot2root-c2: flag planted at /root/flag (root:root 400)" >&2
echo "[entrypoint] serving Phantom Wire panel on 0.0.0.0:${PORT} as www" >&2

export PORT
exec setpriv --reuid=www --regid=www --init-groups \
     /usr/bin/python3 /opt/web/panel.py
