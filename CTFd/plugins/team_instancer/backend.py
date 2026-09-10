"""Live backend: Docker container lifecycle + frpc admin over the dockerproxy.

Design note (deviation from the research doc's voie A): we reach frpc's admin
API by forwarding the arena's 127.0.0.1:7400 through the existing dockerproxy
sidecar (an extra `-L` in its ssh tunnel), so the front talks plain HTTP to
FRPC_ADMIN_ADDR (default dockerproxy:7400). This avoids depending on a
curl-capable image being present on the arena (voie A) and is directly
testable. It exposes the admin API only on the compose-internal network, whose
reach already implies Docker-root on the arena, so it adds no privilege.

Everything here needs the live arena; it is exercised at the Lot 5 rehearsal.
The pure text/allocation logic it relies on lives in frp.py and is unit-tested.
"""

import base64
import fcntl
import urllib.request

from . import frp, settings

# Serializes the frpc config read-modify-write so concurrent spawns/teardowns/
# reaps across gunicorn workers cannot clobber each other's proxy stanzas
# (GET /api/config -> mutate -> PUT overwrites the whole file).
_FRPC_LOCK_PATH = "/tmp/ctfd_instancer_frpc.lock"

# docker SDK is only needed when the instancer is active; import lazily so the
# plugin loads even where the package is absent (e.g. a bare dev CTFd).
try:
    import docker
except Exception:  # pragma: no cover
    docker = None


class InstancerError(Exception):
    pass


def _client():
    if not settings.is_active():
        raise InstancerError("instancier inactif : DOCKER_HOST n'est pas defini")
    if docker is None:
        raise InstancerError("le paquet python 'docker' est absent de l'image CTFd")
    return docker.DockerClient(base_url=settings.DOCKER_HOST, timeout=30)


# --- frpc admin (HTTP through dockerproxy) ---------------------------------

def _frpc_request(method, path, body=None):
    url = f"http://{settings.FRPC_ADMIN_ADDR}{path}"
    data = body.encode() if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, method=method)
    if settings.FRPC_ADMIN_PASSWORD:
        token = base64.b64encode(
            f"{settings.FRPC_ADMIN_USER}:{settings.FRPC_ADMIN_PASSWORD}".encode()
        ).decode()
        req.add_header("Authorization", f"Basic {token}")
    if data is not None:
        req.add_header("Content-Type", "text/plain")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode()


class _FrpcLock:
    """Cross-process/host lock around the frpc config read-modify-write."""

    def __enter__(self):
        self._fh = open(_FRPC_LOCK_PATH, "w")
        fcntl.flock(self._fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        try:
            fcntl.flock(self._fh, fcntl.LOCK_UN)
        finally:
            self._fh.close()


def _frpc_add(name, port):
    with _FrpcLock():
        cfg = _frpc_request("GET", "/api/config")
        _frpc_request("PUT", "/api/config", frp.add_proxy(cfg, name, port))
        _frpc_request("GET", "/api/reload")


def _frpc_remove(name):
    with _FrpcLock():
        cfg = _frpc_request("GET", "/api/config")
        _frpc_request("PUT", "/api/config", frp.remove_proxy(cfg, name))
        _frpc_request("GET", "/api/reload")


# --- Container lifecycle ---------------------------------------------------

def container_name(account_id, challenge_id):
    return f"ti-{account_id}-{challenge_id}"


def _remove_by_name(client, name):
    try:
        client.containers.get(name).remove(force=True)
    except Exception:
        pass


def spawn_container(account_id, challenge, env, port):
    """Create the per-team container, publishing its internal port on the arena
    loopback at `port`. `env` carries the concrete FLAG and the per-challenge
    CHALLENGE_SECRET only — never the team master secret, so owning this
    container cannot yield another challenge's flag. Returns
    (container_id, network_name)."""
    client = _client()
    net_name = f"ctfd_team_{account_id}"
    try:
        client.networks.create(net_name, driver="overlay", attachable=True)
    except Exception:
        pass  # already exists

    # A stale container with the deterministic name would make run() 409. Remove
    # any orphan first so a spawn is never permanently wedged by a name clash.
    name = container_name(account_id, challenge.id)
    _remove_by_name(client, name)

    mem = getattr(challenge, "mem_limit", None) or settings.DEFAULT_MEM_LIMIT
    container = client.containers.run(
        image=challenge.docker_image,          # local image, no registry pull
        detach=True,
        name=name,
        environment=dict(env),
        network=net_name,
        ports={f"{challenge.internal_port}/tcp": ("127.0.0.1", port)},
        labels={
            "ctfd.instancer": "1",
            "ctfd.account": str(account_id),
            "ctfd.challenge": str(challenge.id),
        },
        mem_limit=mem,
        nano_cpus=settings.DEFAULT_NANO_CPUS,
        pids_limit=settings.DEFAULT_PIDS_LIMIT,
        restart_policy={"Name": "no"},
    )
    return container.id, net_name


def teardown(instance):
    """Idempotent teardown: proxy, container, network, port. Never raises on a
    piece that is already gone."""
    if instance.proxy_name:
        try:
            _frpc_remove(instance.proxy_name)
        except Exception:
            pass
    if settings.is_active() and docker is not None:
        try:
            client = _client()
            if instance.container_id:
                try:
                    c = client.containers.get(instance.container_id)
                    c.remove(force=True)
                except Exception:
                    pass
            # Also remove by deterministic name: covers a container that was
            # created but whose id never made it into the row (spawn failure).
            _remove_by_name(client, container_name(instance.account_id, instance.challenge_id))
            if instance.network_name:
                try:
                    net = client.networks.get(instance.network_name)
                    # Only remove the team network if no containers remain on it.
                    net.reload()
                    if not net.containers:
                        net.remove()
                except Exception:
                    pass
        except Exception:
            pass
    frp.release_port(instance.id)


def add_frp_for(instance):
    _frpc_add(instance.proxy_name, instance.port)


def list_live_container_ids():
    """Container ids currently labelled as ours, for reconciliation."""
    client = _client()
    return {
        c.id for c in client.containers.list(
            all=True, filters={"label": "ctfd.instancer=1"}
        )
    }
