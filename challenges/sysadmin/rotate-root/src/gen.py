#!/usr/bin/env python3
"""Deterministic generator for the 'rotate-root' challenge.

Ships an ops bundle (mirrored under ``fs/``) whose pieces, read together, reveal
both *where* a root-written secret token lands and *how* its value is computed:

  * ``etc/cron.d/app-backup``    - a cron job run as the ``deploy`` user.
  * ``etc/logrotate.d/app``      - rotates ``/var/log/app/*.log`` and, in its
                                   ``postrotate`` block (which logrotate runs
                                   **as root**), invokes ``rotate-hook.sh``.
  * ``etc/sudoers.d/deploy``     - lets ``deploy`` run ``rotate-hook.sh`` as root
                                   with NOPASSWD (so the low-priv user can also
                                   trigger the root write on demand).
  * ``usr/local/sbin/rotate-hook.sh`` - the hook. It sources ``rotate.conf`` and
                                   *derives* the rotation token from those values
                                   (documented naming + hashing rule), then
                                   writes it to a path it also derives.
  * ``etc/app/rotate.conf``      - defines ``SECRET_DIR``, ``CYCLE``, ``HOSTID``,
                                   ``ROTATE_SECRET`` and documents the exact
                                   derivation used by the hook.

Crucially the token file itself is **not shipped** (a blind ``grep`` /
``find | cat`` across the bundle turns up nothing). The token is a pure function
of the committed config, so the player must reconstruct it::

    TOKEN = sha256("<CYCLE>:<HOSTID>:<ROTATE_SECRET>").hexdigest()[:10]
    flag  = "NCTF{logrotate_postrotate_root_" + TOKEN + "}"
"""

import hashlib
import os

SECRET_DIR = "/var/lib/app/secrets"
CYCLE = "2024w18"
HOSTID = "kbz07"
# Obviously-fake dev value. On a real host this would be a genuine secret; here
# it is committed alongside the derivation rule so the token is reconstructable.
ROTATE_SECRET = "dev-rotate-secret-0000"


def derive_token() -> str:
    material = f"{CYCLE}:{HOSTID}:{ROTATE_SECRET}"
    return hashlib.sha256(material.encode()).hexdigest()[:10]


ROTATION_TOKEN = derive_token()
FLAG = "NCTF{logrotate_postrotate_root_" + ROTATION_TOKEN + "}"

CRON = """\
# /etc/cron.d/app-backup
# Nightly backup, runs as the unprivileged 'deploy' user.
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MAILTO=ops@kekeli.internal

17 2 * * *  deploy  /usr/local/bin/backup.sh >> /var/log/app/backup.log 2>&1
"""

LOGROTATE = """\
# /etc/logrotate.d/app
/var/log/app/*.log {
    daily
    rotate 7
    missingok
    compress
    # postrotate scripts run AS ROOT (logrotate itself runs as root from
    # /etc/cron.daily). This hook therefore writes with root privileges.
    postrotate
        /usr/local/sbin/rotate-hook.sh >/dev/null 2>&1 || true
    endscript
}
"""

SUDOERS = """\
# /etc/sudoers.d/deploy
# Let the deploy user trigger a rotation hook without a password.
# (Combined with the root postrotate context, this is the privilege path.)
deploy ALL=(root) NOPASSWD: /usr/local/sbin/rotate-hook.sh
"""

ROTATE_CONF = f"""\
# /etc/app/rotate.conf  -- sourced by rotate-hook.sh
SECRET_DIR={SECRET_DIR}
CYCLE={CYCLE}
HOSTID={HOSTID}
# ROTATE_SECRET seeds the derived rotation token (dev value in this snapshot).
ROTATE_SECRET={ROTATE_SECRET}

# Token derivation (see rotate-hook.sh):
#   TOKEN = sha256("<CYCLE>:<HOSTID>:<ROTATE_SECRET>") | first 10 hex chars
# Output file: $SECRET_DIR/app-<CYCLE>-<HOSTID>.token  (mode 0600, root-owned;
# NOT included in this bundle -- reconstruct the token from the values above).
"""

HOOK = """\
#!/bin/sh
# /usr/local/sbin/rotate-hook.sh
# Runs as root (from logrotate postrotate, or via sudo). Derives a rotation
# token from the config and drops it in the secrets dir under a derived name.
set -eu

. /etc/app/rotate.conf

# Derived token filename: app-<CYCLE>-<HOSTID>.token
NAME="app-${CYCLE}-${HOSTID}.token"
OUT="${SECRET_DIR}/${NAME}"

# Derived token value: first 10 hex chars of sha256(CYCLE:HOSTID:ROTATE_SECRET).
# Deterministic, so it is fully reconstructable from rotate.conf.
TOKEN=$(printf '%s:%s:%s' "$CYCLE" "$HOSTID" "$ROTATE_SECRET" \\
    | sha256sum | cut -c1-10)

install -d -m 0700 "$SECRET_DIR"
umask 077
printf '%s\\n' "$TOKEN" > "$OUT"
"""


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))
    fs = os.path.join(root, "fs")

    def w(relpath, content, mode=0o644):
        path = os.path.join(fs, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.chmod(path, mode)

    w("etc/cron.d/app-backup", CRON)
    w("etc/logrotate.d/app", LOGROTATE)
    w("etc/sudoers.d/deploy", SUDOERS)
    w("etc/app/rotate.conf", ROTATE_CONF)
    w("usr/local/sbin/rotate-hook.sh", HOOK, mode=0o755)

    # NOTE: the root-written token file is intentionally NOT shipped. The player
    # must derive the token from rotate.conf; there is nothing to cat.
    stale = os.path.join(fs, "var/lib/app/secrets", f"app-{CYCLE}-{HOSTID}.token")
    if os.path.exists(stale):
        os.remove(stale)

    print("wrote ops bundle under", fs)
    print("derived token:", ROTATION_TOKEN)
    print("flag:", FLAG)


if __name__ == "__main__":
    main()
