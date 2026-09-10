"""Runtime settings for the team instancer.

Everything is read from the environment (written by `make link` into the front
container) with safe defaults, so the plugin never hard-codes deployment values.
The instancer is INACTIVE when DOCKER_HOST is empty (out of event): routes then
return 503 rather than erroring, and the reaper does nothing.
"""

import os


def _int(env, default):
    try:
        return int(os.environ.get(env, "") or default)
    except (TypeError, ValueError):
        return default


# Docker endpoint. Empty out of event -> instancer inactive.
DOCKER_HOST = os.environ.get("DOCKER_HOST", "").strip()

# Public IP/host of the front, used to build connection_info shown to players.
# Written by `make link` (upsert FRONT_PUBLIC_IP). Empty -> connection_info
# falls back to a placeholder the admin can spot.
FRONT_PUBLIC_IP = os.environ.get("FRONT_PUBLIC_IP", "").strip()

# frpc admin API on the arena (reached through an ephemeral --network host
# container over the Docker channel; see backend.FrpAdmin).
FRPC_ADMIN_ADDR = os.environ.get("FRPC_ADMIN_ADDR", "127.0.0.1:7400")
FRPC_ADMIN_USER = os.environ.get("FRPC_ADMIN_USER", "admin")
FRPC_ADMIN_PASSWORD = os.environ.get("FRPC_ADMIN_PASSWORD", "")

# Public TCP port range for per-team instances. MUST match the security-group
# range (whale_port_range_* in Terraform, default 28000-28500).
PORT_RANGE_START = _int("WHALE_PORT_RANGE_START", 28000)
PORT_RANGE_END = _int("WHALE_PORT_RANGE_END", 28500)

# Lifetime of an instance before the reaper tears it down, in seconds.
INSTANCE_TTL = _int("INSTANCER_TTL", 3600)

# Renew: how many times a team may extend one instance, and by how long.
MAX_RENEW_COUNT = _int("INSTANCER_MAX_RENEW", 5)

# Admission controls.
MAX_PER_TEAM = _int("INSTANCER_MAX_PER_TEAM", 3)      # concurrent instances / team
MAX_TOTAL = _int("INSTANCER_MAX_TOTAL", 480)          # global cap; < port-range size
SPAWN_RATELIMIT = os.environ.get("INSTANCER_SPAWN_RATELIMIT", "6/minute")

# Reaper cadence (seconds). Deliberately not too aggressive: our Docker channel
# is a single ssh tunnel, so we avoid hammering it.
REAP_INTERVAL = _int("INSTANCER_REAP_INTERVAL", 30)

# Per-container resource limits (defaults; a challenge may override via extra).
DEFAULT_MEM_LIMIT = os.environ.get("INSTANCER_MEM_LIMIT", "128m")
DEFAULT_NANO_CPUS = _int("INSTANCER_NANO_CPUS", 500_000_000)  # 0.5 CPU
DEFAULT_PIDS_LIMIT = _int("INSTANCER_PIDS_LIMIT", 256)


def is_active():
    """The instancer only operates when a Docker endpoint is configured."""
    return bool(DOCKER_HOST)
