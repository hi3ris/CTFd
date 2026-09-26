#!/usr/bin/env python3
"""Deterministic generator for the 'alias-slip' challenge.

Ships an nginx site config with the classic *alias off-by-slash* traversal, plus
a copy of the server's document tree so the traversal resolves against real
shipped files.

The vulnerable block is::

    location /assets {
        alias /srv/kekeli/public/assets/;
    }

Because the ``location`` has no trailing slash but the ``alias`` does, a request
for ``/assets../config/settings.py.bak`` is mapped by nginx to
``/srv/kekeli/public/assets/../config/settings.py.bak`` =
``/srv/kekeli/public/config/settings.py.bak`` — a *sibling* of the assets
directory, outside what the block was meant to expose. That backup file is a
stale editor ``.bak`` that still contains the admin token used as the flag.
"""

import os

ADMIN_TOKEN = "a7f3c0de91"
FLAG = "NCTF{nginx_alias_offbyslash_" + ADMIN_TOKEN + "}"

# Server document root, mirrored under webroot/ so paths resolve for real.
DOC_ROOT = "srv/kekeli/public"

NGINX_CONF = """\
# /etc/nginx/sites-enabled/kekeli.conf
server {
    listen 80;
    server_name kekeli.internal;
    root /srv/kekeli/public;
    index index.html;

    # Static assets. NOTE: 'location' has no trailing slash but 'alias' does.
    # (copied from a stackoverflow answer during the crunch, ticket OPS-91)
    location /assets {
        alias /srv/kekeli/public/assets/;
        autoindex off;
    }

    location / {
        try_files $uri $uri/ =404;
    }

    # App config directory is meant to be private; only the app user reads it.
    location /config {
        deny all;
        return 403;
    }
}
"""

INDEX_HTML = """\
<!doctype html>
<title>Kekeli</title>
<h1>Kekeli internal portal</h1>
<p>Nothing to see here.</p>
"""

LOGO_TXT = "kekeli-logo-placeholder\n"

# The exposed backup: a stale copy of the app settings, holding the admin token.
# The token itself is the flag body (no NCTF{ marker here, so grepping the
# bundle for the flag finds nothing).
SETTINGS_BAK = f"""\
# settings.py.bak  (auto-saved by the editor, forgot to delete -- OPS-91)
DEBUG = False
DB_URL = "postgres://api:api@db:5432/api"

# Long-lived admin API token. Rotate quarterly (we never do).
ADMIN_API_TOKEN = "{ADMIN_TOKEN}"

ALLOWED_HOSTS = ["kekeli.internal"]
"""


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))

    with open(os.path.join(root, "nginx.conf"), "w", encoding="utf-8") as fh:
        fh.write(NGINX_CONF)

    base = os.path.join(root, "webroot", DOC_ROOT)
    os.makedirs(os.path.join(base, "assets"), exist_ok=True)
    os.makedirs(os.path.join(base, "config"), exist_ok=True)

    with open(os.path.join(base, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(INDEX_HTML)
    with open(os.path.join(base, "assets", "logo.txt"), "w", encoding="utf-8") as fh:
        fh.write(LOGO_TXT)
    with open(
        os.path.join(base, "config", "settings.py.bak"), "w", encoding="utf-8"
    ) as fh:
        fh.write(SETTINGS_BAK)

    print("wrote nginx.conf and webroot/ under", root)
    print("flag:", FLAG)


if __name__ == "__main__":
    main()
