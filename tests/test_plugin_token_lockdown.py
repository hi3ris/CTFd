"""token_lockdown plugin — token creation is admins-only and the hibris
"Access Tokens" tab is hidden from players.

The plugin only takes effect when plugins are loaded, so every case builds the
app with ``enable_plugins=True`` (create_ctfd runs in SAFE_MODE otherwise).
"""
from CTFd.models import Tokens, Users
from CTFd.utils.security.auth import generate_user_token
from tests.helpers import create_ctfd, destroy_ctfd, gen_user, login_as_user


def test_player_cannot_create_token():
    """A regular player POSTing /api/v1/tokens is refused, no token stored"""
    app = create_ctfd(enable_plugins=True)
    with app.app_context():
        gen_user(app.db, name="player")
        with login_as_user(app, "player") as client:
            r = client.post("/api/v1/tokens", json={})
            assert r.status_code == 403
        assert Tokens.query.count() == 0
    destroy_ctfd(app)


def test_admin_can_still_create_token():
    """The admin keeps the deploy token ctfcli/preflight rely on"""
    app = create_ctfd(enable_plugins=True)
    with app.app_context():
        admin_id = Users.query.filter_by(name="admin").first().id
        with login_as_user(app, "admin") as client:
            r = client.post("/api/v1/tokens", json={})
            assert r.status_code == 200
            value = r.get_json()["data"]["value"]
            token = Tokens.query.filter_by(value=value).first()
            assert token is not None
            assert token.user_id == admin_id
    destroy_ctfd(app)


def test_existing_token_still_listable_and_deletable():
    """Creation is gated, but GET/DELETE on existing tokens are untouched"""
    app = create_ctfd(enable_plugins=True)
    with app.app_context():
        user = gen_user(app.db, name="player")
        token = generate_user_token(user)
        token_id = token.id
        with login_as_user(app, "player") as client:
            r = client.get("/api/v1/tokens", json="")
            assert r.status_code == 200
            assert len(r.get_json()["data"]) == 1

            r = client.delete("/api/v1/tokens/" + str(token_id), json="")
            assert r.status_code == 200
        assert Tokens.query.count() == 0
    destroy_ctfd(app)


def test_hibris_tab_hidden_from_players_shown_to_admin():
    """hibris Settings shows the Access Tokens tab only to admins"""
    app = create_ctfd(enable_plugins=True, ctf_theme="hibris")
    with app.app_context():
        gen_user(app.db, name="player")

        with login_as_user(app, "player") as client:
            body = client.get("/settings").get_data(as_text=True)
            assert "Access Tokens" not in body
            assert 'id="settings-tokens-tab"' not in body

        with login_as_user(app, "admin") as client:
            body = client.get("/settings").get_data(as_text=True)
            assert "Access Tokens" in body
            assert 'id="settings-tokens-tab"' in body
    destroy_ctfd(app)
