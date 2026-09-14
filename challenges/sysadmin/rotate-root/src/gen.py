#!/usr/bin/env python3
"""Deterministic generator for the 'rotate-root' challenge.

Ships an ops bundle (mirrored under ``fs/``) whose pieces, read together, reveal
where a root-written secret token lands:

  * ``etc/cron.d/app-backup``    - a cron job run as the ``deploy`` user.
  * ``etc/logrotate.d/app``      - rotates ``/var/log/app/*.log`` and, in its
                                   ``postrotate`` block (which logrotate runs
                                   **as root**), invokes ``rotate-hook.sh``.
  * ``etc/sudoers.d/deploy``     - lets ``deploy`` run ``rotate-hook.sh`` as root
                                   with NOPASSWD (so the low-priv user can also
                                   trigger the root write on demand).
  * ``usr/local/sbin/rotate-hook.sh`` - the hook. It sources ``rotate.conf`` and
                                   writes a fresh token to a path it *derives*
                                   from those values.
  * ``etc/app/rotate.conf``      - defines ``SECRET_DIR``, ``CYCLE``, ``HOSTID``.
  * ``var/lib/app/secrets/<derived>.token`` - the root-owned secret token,
                                   sitting at the deducible path.

The token file holds only a raw rotation token (no ``NCTF{`` marker, so a blind
``grep`` across the bundle finds nothing). The flag is that token wrapped in the
documented format::

    flag = "NCTF{logrotate_postrotate_root_" + ROTATION_TOKEN + "}"

You must deduce the path from the config chain, read the raw token, and wrap it.
"""

import os

ROTATION_TOKEN = "9f3ac1d20b"
FLAG = "NCTF{logrotate_postrotate_root_" + ROTATION_TOKEN + "}"

SECRET_DIR = "/var/lib/app/secrets"
CYCLE = "2024w18"
HOSTID = "kbz07"

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
"""

HOOK = """\
#!/bin/sh
# /usr/local/sbin/rotate-hook.sh
# Runs as root (from logrotate postrotate, or via sudo). Mints a rotation token
# and drops it in the secrets dir under a name derived from the config.
set -eu

. /etc/app/rotate.conf

# Derived token filename: app-<CYCLE>-<HOSTID>.token
NAME="app-${CYCLE}-${HOSTID}.token"
OUT="${SECRET_DIR}/${NAME}"

# Freshly minted per rotation (random). The shipped host snapshot captured the
# most recent value in the file below.
ROTATION_TOKEN="$(openssl rand -hex 5)"

install -d -m 0700 "$SECRET_DIR"
umask 077
printf '%s\\n' "$ROTATION_TOKEN" > "$OUT"
"""


def derived_name() -> str:
    return f"app-{CYCLE}-{HOSTID}.token"


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

    # The root-written secret, at the deducible path. Holds only the raw token.
    token_rel = os.path.join("var/lib/app/secrets", derived_name())
    w(token_rel, ROTATION_TOKEN + "\n", mode=0o600)

    print("wrote ops bundle under", fs)
    print("token path:", "/" + token_rel)
    print("flag:", FLAG)


if __name__ == "__main__":
    main()
