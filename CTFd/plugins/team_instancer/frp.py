"""FRP wiring: port allocation and frpc.toml read-modify-write.

The pure text functions here (proxy_block, add_proxy, remove_proxy) are the
statically-testable core. The live calls to frpc's admin API go through the
Docker channel in backend.py (an ephemeral --network host container that curls
127.0.0.1:7400 on the arena), because that admin port is not otherwise
reachable from the front.

We key each proxy on `t<account>-c<challenge>` and use localPort == remotePort
so a single allocation covers both the arena loopback port and the frps port.
"""

import re

from . import settings


def proxy_name(account_id, challenge_id):
    return f"t{account_id}-c{challenge_id}"


def proxy_block(name, port):
    """One TCP proxy stanza (frp 0.61.x TOML). localIP is the arena loopback:
    the container is published on 127.0.0.1:<port> of the arena, and frpc runs
    in the host netns, so 127.0.0.1 always reaches it (the overlay IP would
    not)."""
    return (
        "\n[[proxies]]\n"
        f'name = "{name}"\n'
        'type = "tcp"\n'
        'localIP = "127.0.0.1"\n'
        f"localPort = {port}\n"
        f"remotePort = {port}\n"
    )


_PROXY_RE_TMPL = (
    r"\n\[\[proxies\]\]\n"
    r'name = "{name}"\n'
    r"(?:(?!\n\[\[proxies\]\]).)*"
)


def has_proxy(config_text, name):
    return re.search(_PROXY_RE_TMPL.format(name=re.escape(name)), config_text, re.S) is not None


def add_proxy(config_text, name, port):
    """Append a proxy stanza unless one with the same name already exists
    (idempotent)."""
    if has_proxy(config_text, name):
        return config_text
    return config_text.rstrip("\n") + "\n" + proxy_block(name, port)


def remove_proxy(config_text, name):
    """Strip the stanza whose name matches (idempotent: a no-op if absent)."""
    return re.sub(
        _PROXY_RE_TMPL.format(name=re.escape(name)), "", config_text, flags=re.S
    ).rstrip("\n") + "\n"


# --- Port allocation -------------------------------------------------------

def allocate_port(instance_id, account_id, challenge_id):
    """Claim a free port atomically. Uses SELECT ... FOR UPDATE SKIP LOCKED on
    MariaDB 10.6+; callers on older MariaDB should set SKIP_LOCKED=False (the
    serialization is acceptable at this scale)."""
    from .models import FrpPort, db
    q = (
        FrpPort.query.filter(FrpPort.instance_id.is_(None))
        .order_by(FrpPort.port.asc())
    )
    if settings.is_active():
        try:
            q = q.with_for_update(skip_locked=True)
        except Exception:
            q = q.with_for_update()
    row = q.first()
    if row is None:
        return None
    row.instance_id = instance_id
    row.account_id = account_id
    row.challenge_id = challenge_id
    db.session.commit()
    return row.port


def release_port(instance_id):
    """Free every port held by an instance (idempotent)."""
    from .models import FrpPort, db
    FrpPort.query.filter_by(instance_id=instance_id).update(
        {"instance_id": None, "account_id": None, "challenge_id": None}
    )
    db.session.commit()


def ensure_port_pool():
    """Populate frp_port with the configured range if empty. Called from load()."""
    from .models import FrpPort, db
    if db.session.query(FrpPort.port).first() is not None:
        return
    db.session.bulk_save_objects(
        [FrpPort(port=p) for p in range(settings.PORT_RANGE_START, settings.PORT_RANGE_END + 1)]
    )
    db.session.commit()
