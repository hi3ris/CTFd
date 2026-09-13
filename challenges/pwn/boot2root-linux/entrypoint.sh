#!/bin/sh
# Container entrypoint for boot2root-linux.
#
# Runs as ROOT at startup so it can plant the flag where only root can read it,
# then permanently drops to the unprivileged `www` user to serve the foothold.
#
# 1. Derive THIS instance's flag via flag.py (reads injected FLAG /
#    CHALLENGE_SECRET -- see flag.py). The flag is never baked into the image.
# 2. Write it to /root/flag, mode 400, owned by root:root. It is the ONLY copy
#    on the box and is not world-readable -- a player must actually become root
#    to read it. Reading it as root IS the win condition (effect-based).
# 3. Drop privileges to `www` and exec the network-facing status service. From
#    that unprivileged shell the player must climb the local privesc chain.
set -eu

# --- 1 + 2: plant the root-only flag --------------------------------------
FLAG="$(python3 /opt/flag.py)"
printf '%s\n' "$FLAG" > /root/flag
chown root:root /root/flag
chmod 400 /root/flag
# scrub the flag from root's environment so it survives only in the file; the
# foothold service (started below as www) is never given FLAG in its env.
unset FLAG

PORT="${PORT:-8080}"
echo "[entrypoint] boot2root-linux: flag planted at /root/flag (root:root 400)" >&2
echo "[entrypoint] serving NodeStatus on 0.0.0.0:${PORT} as www" >&2

# --- 3: drop to www and serve the foothold --------------------------------
# setpriv (util-linux) reassigns real+effective+saved uid/gid and rebuilds the
# supplementary groups, so the service has no residual root privilege.
export PORT
exec setpriv --reuid=www --regid=www --init-groups \
     /usr/bin/python3 /opt/web/webstatus.py
