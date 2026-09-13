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

# How a spawned container is made reachable by players.
#   frp    (default, production): container published on the arena loopback,
#          then exposed through a frpc proxy stanza (see frp.py / backend.py).
#          Requires FRPC_ADMIN_ADDR and a Swarm overlay network.
#   direct (local validation): container published straight on the Docker
#          host (0.0.0.0:<port>) on a plain bridge network, no frp at all.
#          Used by deploy/local/ to run the whole platform on one laptop.
PUBLISH = os.environ.get("INSTANCER_PUBLISH", "frp").strip().lower() or "frp"
if PUBLISH not in ("frp", "direct"):
    raise RuntimeError(f"INSTANCER_PUBLISH must be 'frp' or 'direct', got {PUBLISH!r}")

# Local only: force the model name AI containers ask for (they default to
# llama3.1:8b, which is heavy on a CPU laptop). Empty -> not injected.
OLLAMA_MODEL_OVERRIDE = os.environ.get("INSTANCER_OLLAMA_MODEL", "").strip()

# Public IP/host of the front, used to build connection_info shown to players.
# Written by `make link` (upsert FRONT_PUBLIC_IP). Empty -> connection_info
# falls back to a placeholder the admin can spot.
FRONT_PUBLIC_IP = os.environ.get("FRONT_PUBLIC_IP", "").strip()

# AI admission gateway on the front. AI challenge containers are pointed at this
# (as their OLLAMA_URL) instead of the GPU node directly, so all model traffic
# goes through one admission point. Empty -> AI challenges cannot spawn.
AI_PROXY_URL = os.environ.get("AI_PROXY_URL", "").strip()

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


def uses_frp():
    """True in production: the frpc proxy is part of the publish path."""
    return PUBLISH == "frp"


def network_driver():
    """overlay needs Swarm (the arena); a laptop's Docker only has bridge."""
    return "overlay" if uses_frp() else "bridge"


def port_binding(port):
    """Host-side binding for the container port. On the arena the container is
    only reachable through frp, so bind loopback; locally players hit the host
    directly, so bind every interface."""
    return ("127.0.0.1", port) if uses_frp() else ("0.0.0.0", port)


def extra_hosts():
    """Locally, AI containers must reach the ai-gateway published on the Docker
    host: give them host.docker.internal (Docker Desktop has it natively;
    'host-gateway' makes it work on Linux too). Not needed behind frp, where
    AI_PROXY_URL is the front's private IP."""
    return {} if uses_frp() else {"host.docker.internal": "host-gateway"}
