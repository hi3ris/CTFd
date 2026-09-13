"""The hibris theme must render every participant-facing page without a CTFd
tell, and every asset its templates reference must resolve. Runs on SQLite
with the plugins loaded, so it needs no Docker — `make test` catches a broken
template or a missing static file before anything reaches AWS."""
import os
import re

from tests.helpers import create_ctfd, destroy_ctfd, login_as_user, register_user, setup_ctfd

os.environ.setdefault("CTF_TEAM_FLAG_SECRET", "test-secret")


def _app():
    app = create_ctfd(enable_plugins=True, setup=False)
    # CTFd registers its theme-asset url_defaults (the ".min"/".dev" suffix and
    # the ?d= cache-buster) on `current_app` when CTFd.utils.helpers is first
    # imported, i.e. on the FIRST app of the process only. Production has one
    # app so it never matters; in a test process every app after the first
    # would render "css/main.css" and 404. Re-attach the hooks — before the
    # first request, as Flask requires — so this test sees the URLs a real
    # server renders, whatever the test order.
    from CTFd.utils.helpers import asset_cache_url_default, env_asset_url_default
    for fn in (env_asset_url_default, asset_cache_url_default):
        if fn not in app.url_default_functions.get(None, []):
            app.url_defaults(fn)
    return setup_ctfd(app, ctf_name="NCTF25", user_mode="teams", ctf_theme="hibris")


def test_public_pages_render_with_hibris_branding():
    app = _app()
    with app.app_context():
        client = app.test_client()
        for path in ("/", "/login", "/register", "/scoreboard", "/users", "/teams"):
            r = client.get(path)
            assert r.status_code == 200, path
            html = r.get_data(as_text=True)
            assert "family=Tourney" in html, f"{path}: hibris fonts not loaded"
            assert "Powered by <strong>Hibris</strong>" in html, f"{path}: footer credit missing"
            assert "Organisé par CERT.tg" in html, f"{path}: organizer credit missing"
            assert "Powered by CTFd" not in html, f"{path}: CTFd tell leaked"
        home = client.get("/").get_data(as_text=True)
        assert 'name="theme-color" content="#00040d"' in home
        assert 'img/cert.png' in home
    destroy_ctfd(app)


def test_error_pages_are_terminal_styled_and_french():
    app = _app()
    with app.app_context():
        r = app.test_client().get("/this-does-not-exist")
        assert r.status_code == 404
        html = r.get_data(as_text=True)
        assert 'class="term-window"' in html
        assert "ressource introuvable" in html
        assert "GET /this-does-not-exist" in html
        assert "File not found" not in html
        from flask import render_template
        for code in ("403", "404", "429", "500", "502"):
            with app.test_request_context(f"/x/{code}"):
                html = render_template(f"errors/{code}.html", error="boom")
                assert 'class="term-window"' in html and f">{code}<" in html, code
    destroy_ctfd(app)


def test_every_referenced_theme_asset_resolves():
    app = _app()
    with app.app_context():
        anon = app.test_client()
        register_user(app)
        authed = login_as_user(app)
        pages = [(anon, "/"), (anon, "/login"), (anon, "/scoreboard"), (anon, "/users"),
                 (authed, "/settings"), (authed, "/notifications")]
        seen, broken = set(), []
        for client, path in pages:
            html = client.get(path, follow_redirects=True).get_data(as_text=True)
            for url in re.findall(r'(?:href|src)="(/themes/[^"]+)"', html):
                key = url.split("?")[0]
                if key in seen:
                    continue
                seen.add(key)
                if anon.get(url).status_code != 200:
                    broken.append(key)
        assert seen, "no theme assets referenced at all?"
        assert not broken, f"theme assets 404: {broken}"
        for url in ("/plugins/team_instancer/assets/view.js", "/plugins/team_instancer/assets/view.html"):
            assert anon.get(url).status_code == 200, url
    destroy_ctfd(app)


def test_plugins_register_their_types():
    app = _app()
    with app.app_context():
        from CTFd.plugins.challenges import CHALLENGE_CLASSES
        from CTFd.plugins.flags import FLAG_CLASSES
        assert "team_instance" in CHALLENGE_CLASSES
        assert "team_hmac" in FLAG_CLASSES
    destroy_ctfd(app)
