"""Writeups plugin: an admin-toggleable in-app page that renders per-challenge
Markdown from writeups/<category>/<slug>.md.

Runs on SQLite with plugins loaded (no Docker). A temp WRITEUPS_DIR holds one
sample writeup carrying a real-looking flag, so we can pin the visibility gate,
the admin preview, the toggle, flag redaction, and path safety.
"""

import os

from CTFd.utils import set_config
from tests.helpers import create_ctfd, destroy_ctfd, login_as_user

os.environ.setdefault("CTF_TEAM_FLAG_SECRET", "test-secret")

REAL_FLAG = "NCTF{a_real_static_flag_leaks}"


def _with_writeups(monkeypatch, tmp_path):
    base = tmp_path / "writeups"
    (base / "web").mkdir(parents=True)
    (base / "web" / "demo.md").write_text(
        f"# Demo Writeup\n\n**Catégorie** web\n\nThe flag was {REAL_FLAG} — nice.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WRITEUPS_DIR", str(base))
    return base


def test_hidden_from_players_by_default(monkeypatch, tmp_path):
    _with_writeups(monkeypatch, tmp_path)
    app = create_ctfd(enable_plugins=True)
    try:
        client = app.test_client()
        r = client.get("/plugins/writeups/")
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "publiés" in body or "publi" in body  # "not published yet" notice
        assert "demo" not in body.lower()
        # a direct writeup URL bounces back to the index while hidden
        r = client.get("/plugins/writeups/web/demo")
        assert r.status_code in (301, 302)
    finally:
        destroy_ctfd(app)


def test_admin_previews_while_hidden(monkeypatch, tmp_path):
    _with_writeups(monkeypatch, tmp_path)
    app = create_ctfd(enable_plugins=True)
    try:
        admin = login_as_user(app, name="admin", password="password")
        r = admin.get("/plugins/writeups/")
        assert r.status_code == 200
        assert "Demo Writeup" in r.get_data(as_text=True)  # tree visible to admin
        # admin can open the writeup even while hidden
        r = admin.get("/plugins/writeups/web/demo")
        assert r.status_code == 200
    finally:
        destroy_ctfd(app)


def test_visible_renders_and_redacts_flag(monkeypatch, tmp_path):
    _with_writeups(monkeypatch, tmp_path)
    app = create_ctfd(enable_plugins=True)
    try:
        with app.app_context():
            set_config("writeups_visible", "true")
        client = app.test_client()
        r = client.get("/plugins/writeups/")
        assert r.status_code == 200
        assert "Demo Writeup" in r.get_data(as_text=True)
        r = client.get("/plugins/writeups/web/demo")
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "NCTF{…}" in body  # redacted
        assert REAL_FLAG not in body  # real flag never served
    finally:
        destroy_ctfd(app)


def test_bad_path_is_rejected(monkeypatch, tmp_path):
    _with_writeups(monkeypatch, tmp_path)
    app = create_ctfd(enable_plugins=True)
    try:
        with app.app_context():
            set_config("writeups_visible", "true")
        client = app.test_client()
        assert client.get("/plugins/writeups/web/missing").status_code == 404
        # an unsafe category (dots) never matches the slug allowlist
        assert client.get("/plugins/writeups/..%2f..%2fetc/passwd").status_code == 404
    finally:
        destroy_ctfd(app)


def test_admin_toggle_flips_config(monkeypatch, tmp_path):
    _with_writeups(monkeypatch, tmp_path)
    app = create_ctfd(enable_plugins=True)
    try:
        admin = login_as_user(app, name="admin", password="password")
        page = admin.get("/plugins/writeups/admin").get_data(as_text=True)
        import re

        m = re.search(r'name="nonce"\s+value="([0-9a-f]+)"', page)
        assert m, "admin page should carry a CSRF nonce"
        r = admin.post(
            "/plugins/writeups/admin/toggle",
            data={"visible": "true", "nonce": m.group(1)},
        )
        assert r.status_code in (200, 302)
        # now a fresh player sees the writeup
        assert app.test_client().get("/plugins/writeups/web/demo").status_code == 200
    finally:
        destroy_ctfd(app)
