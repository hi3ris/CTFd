"""team_min_size plugin — an incomplete team cannot submit flags until it
reaches ``team_size_min`` members; complete teams and admins are unaffected.
"""

from CTFd.models import Users
from CTFd.utils import set_config
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_challenge,
    gen_flag,
    gen_team,
    login_as_user,
)


def _attempt(client, challenge_id):
    return client.post(
        "/api/v1/challenges/attempt",
        json={"challenge_id": challenge_id, "submission": "flag"},
    )


def test_incomplete_team_cannot_submit():
    app = create_ctfd(enable_plugins=True, user_mode="teams")
    with app.app_context():
        set_config("team_size_min", 4)
        chal = gen_challenge(app.db)
        gen_flag(app.db, challenge_id=chal.id, content="flag")
        chal_id = chal.id
        team_id = gen_team(app.db, name="trio", member_count=3).id
        captain = Users.query.filter_by(team_id=team_id).first().name
        with login_as_user(app, name=captain) as client:
            r = _attempt(client, chal_id)
            assert r.status_code == 403
            data = r.get_json()["data"]
            assert data["status"] == "incorrect"
            assert "3 membres sur 4" in data["message"]
    destroy_ctfd(app)


def test_complete_team_can_submit():
    app = create_ctfd(enable_plugins=True, user_mode="teams")
    with app.app_context():
        set_config("team_size_min", 4)
        chal = gen_challenge(app.db)
        gen_flag(app.db, challenge_id=chal.id, content="flag")
        chal_id = chal.id
        team_id = gen_team(app.db, name="quatuor", member_count=4).id
        captain = Users.query.filter_by(team_id=team_id).first().name
        with login_as_user(app, name=captain) as client:
            r = _attempt(client, chal_id)
            assert r.status_code == 200
            assert r.get_json()["data"]["status"] == "correct"
    destroy_ctfd(app)


def test_disabled_when_unset():
    app = create_ctfd(enable_plugins=True, user_mode="teams")
    with app.app_context():
        chal = gen_challenge(app.db)
        gen_flag(app.db, challenge_id=chal.id, content="flag")
        chal_id = chal.id
        team_id = gen_team(app.db, name="solo", member_count=1).id
        captain = Users.query.filter_by(team_id=team_id).first().name
        with login_as_user(app, name=captain) as client:
            r = _attempt(client, chal_id)
            assert r.status_code == 200
    destroy_ctfd(app)
