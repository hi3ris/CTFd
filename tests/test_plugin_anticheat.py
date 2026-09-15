"""Flag-sharing detector (plugins/anticheat).

Runs on SQLite with plugins loaded. Pins the detection rule -- a wrong
submission that is exactly another account's team_hmac flag is an incident,
anything else is not -- plus the cursor/cache behaviour, the CSV export and
the admin-only gate.
"""
import os

from CTFd.models import Fails, Flags
from CTFd.plugins import anticheat
from CTFd.plugins.team_hmac_flag import expected_flag
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_challenge,
    gen_fail,
    gen_flag,
    gen_team,
    login_as_user,
    setup_ctfd,
)

os.environ.setdefault("CTF_TEAM_FLAG_SECRET", "test-secret")


def _teams_app():
    app = create_ctfd(enable_plugins=True, setup=False)
    return setup_ctfd(app, user_mode="teams", ctf_theme="hibris", ctf_name="NCTF26")


def _fixture(db):
    """Two teams, one team_hmac challenge (slug web-jwt) and one static one.
    Returns plain ids/names (ORM objects detach on commit)."""
    a = gen_team(db, name="alpha", email="a@x.com")
    b = gen_team(db, name="bravo", email="b@x.com")
    a_id, b_id = a.id, b.id
    a_user, b_user = a.members[0].id, b.members[0].id
    b_login = b.members[0].name
    hmac_chal = gen_challenge(db, name="JWT cousin", category="web").id
    gen_flag(db, challenge_id=hmac_chal, content="web-jwt", type="team_hmac")
    static_chal = gen_challenge(db, name="Warmup", category="warmup").id
    gen_flag(db, challenge_id=static_chal, content="NCTF{static}", type="static")
    return {
        "a": a_id,
        "b": b_id,
        "a_user": a_user,
        "b_user": b_user,
        "b_login": b_login,
        "hmac": hmac_chal,
        "static": static_chal,
    }


def _clear():
    anticheat.cache.delete(anticheat.CACHE_KEY)


def test_shared_flag_is_an_incident():
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db

        f = _fixture(db)
        _clear()
        # B submits A's flag (with the whitespace a copy-paste often adds)
        shared = expected_flag(f["a"], "web-jwt")
        gen_fail(
            db,
            user_id=f["b_user"],
            team_id=f["b"],
            challenge_id=f["hmac"],
            ip="10.0.0.7",
            provided="  " + shared + "\n",
        )
        st = anticheat.incidents()
        assert len(st["incidents"]) == 1
        inc = st["incidents"][0]
        assert inc["submitter_id"] == f["b"] and inc["submitter"] == "bravo"
        assert inc["owner_id"] == f["a"] and inc["owner"] == "alpha"
        assert inc["challenge_id"] == f["hmac"] and inc["challenge"] == "JWT cousin"
        assert inc["ip"] == "10.0.0.7"
        assert inc["date"]
        assert st["cursor"] == Fails.query.order_by(Fails.id.desc()).first().id
    destroy_ctfd(app)


def test_own_random_and_static_flags_are_not_incidents():
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db

        f = _fixture(db)
        _clear()
        own = expected_flag(f["a"], "web-jwt")
        # own flag of the same challenge (a Fail that would not normally exist)
        gen_fail(db, f["a_user"], f["a"], f["hmac"], provided=own)
        # random garbage
        gen_fail(db, f["b_user"], f["b"], f["hmac"], provided="NCTF{nope}")
        # A's own flag of ANOTHER slug submitted by A on the hmac challenge
        gen_fail(
            db,
            f["a_user"],
            f["a"],
            f["hmac"],
            provided=expected_flag(f["a"], "pwn-other"),
        )
        # A's flag of the hmac challenge submitted by B on the STATIC challenge:
        # not a team_hmac challenge, so ignored
        gen_fail(db, f["b_user"], f["b"], f["static"], provided=own)
        # static wrong flag
        gen_fail(db, f["b_user"], f["b"], f["static"], provided="NCTF{static2}")
        st = anticheat.incidents()
        assert st["incidents"] == []
        # cursor still advanced past every fail
        assert st["cursor"] == Fails.query.order_by(Fails.id.desc()).first().id
    destroy_ctfd(app)


def test_cursor_is_incremental_and_rebuild_replays():
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db

        f = _fixture(db)
        _clear()
        shared = expected_flag(f["a"], "web-jwt")
        gen_fail(db, f["b_user"], f["b"], f["hmac"], provided=shared)
        st1 = anticheat.incidents()
        assert len(st1["incidents"]) == 1
        c1 = st1["cursor"]

        # Nothing new -> same state, and the scan starts after the cursor
        seen = []
        real_scan = anticheat.scan
        anticheat.scan = lambda since_id=0: (
            seen.append(since_id),
            real_scan(since_id),
        )[1]
        try:
            st2 = anticheat.incidents()
        finally:
            anticheat.scan = real_scan
        assert seen == [c1]
        assert st2["incidents"] == st1["incidents"]

        # A second incident is appended, not recomputed from scratch
        gen_fail(
            db,
            f["a_user"],
            f["a"],
            f["hmac"],
            provided=expected_flag(f["b"], "web-jwt"),
        )
        st3 = anticheat.incidents()
        assert [i["submitter"] for i in st3["incidents"]] == ["bravo", "alpha"]
        assert st3["cursor"] > c1

        # rebuild replays the whole history and reaches the same result
        st4 = anticheat.incidents(rebuild=True)
        assert st4["incidents"] == st3["incidents"]

        # a team_hmac flag added later on a challenge with old fails: only a
        # rebuild sees it
        chal = gen_challenge(db, name="Late").id
        gen_fail(db, f["b_user"], f["b"], chal, provided=expected_flag(f["a"], "late"))
        anticheat.incidents()
        gen_flag(db, challenge_id=chal, content="late", type="team_hmac")
        assert len(anticheat.incidents()["incidents"]) == 2
        assert len(anticheat.incidents(rebuild=True)["incidents"]) == 3
    destroy_ctfd(app)


def test_real_submission_path_creates_incident():
    """B pastes A's flag into the challenge modal: the Fail written by CTFd's
    own attempt endpoint is what the detector reads."""
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db

        f = _fixture(db)
        _clear()
        client = login_as_user(app, name=f["b_login"], password="password")
        r = client.post(
            "/api/v1/challenges/attempt",
            json={
                "challenge_id": f["hmac"],
                "submission": expected_flag(f["a"], "web-jwt"),
            },
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["status"] == "incorrect"
        # and B's OWN flag is accepted, proving the fixture flag is real
        r = client.post(
            "/api/v1/challenges/attempt",
            json={
                "challenge_id": f["hmac"],
                "submission": expected_flag(f["b"], "web-jwt"),
            },
        )
        assert r.get_json()["data"]["status"] == "correct"

        st = anticheat.incidents()
        assert len(st["incidents"]) == 1
        assert st["incidents"][0]["submitter"] == "bravo"
        assert st["incidents"][0]["owner"] == "alpha"
    destroy_ctfd(app)


def test_api_admin_only_json_csv_and_since():
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db

        f = _fixture(db)
        _clear()
        gen_fail(
            db,
            f["b_user"],
            f["b"],
            f["hmac"],
            ip="=1+1",
            provided=expected_flag(f["a"], "web-jwt"),
        )
        first_id = Fails.query.order_by(Fails.id.desc()).first().id
        gen_fail(
            db,
            f["a_user"],
            f["a"],
            f["hmac"],
            provided=expected_flag(f["b"], "web-jwt"),
        )

        # player: 403 on JSON, redirect to login on the page
        player = login_as_user(app, name=f["b_login"], password="password")
        r = player.get(
            "/plugins/anticheat/api/incidents", content_type="application/json"
        )
        assert r.status_code == 403
        r = player.get("/plugins/anticheat/admin")
        assert r.status_code == 302 and "/login" in r.headers["Location"]

        admin = login_as_user(app, name="admin", password="password")
        r = admin.get("/plugins/anticheat/api/incidents")
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert d["mode"] == "teams" and d["hmac_challenges"] == 1
        assert d["total"] == 2 and d["count"] == 2
        assert d["accounts"] == 2

        r = admin.get("/plugins/anticheat/api/incidents?since_id=%d" % first_id)
        d = r.get_json()["data"]
        assert d["total"] == 2 and d["count"] == 1
        assert d["incidents"][0]["submitter"] == "alpha"

        r = admin.get("/plugins/anticheat/api/incidents?format=csv")
        assert r.status_code == 200 and r.mimetype == "text/csv"
        lines = r.get_data(as_text=True).splitlines()
        assert lines[0].startswith("date,fail_id,submitter")
        assert len(lines) == 3
        assert "'=1+1" in lines[1]  # formula-injection guard on the IP cell

        r = admin.get("/plugins/anticheat/admin")
        assert r.status_code == 200
        assert "Anti-triche" in r.get_data(as_text=True)
        assert "/plugins/anticheat/api/incidents" in r.get_data(as_text=True)
    destroy_ctfd(app)


def test_no_hmac_flags_means_no_incidents_and_cursor_moves():
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db

        f = _fixture(db)
        Flags.query.filter_by(type="team_hmac").delete()
        db.session.commit()
        _clear()
        gen_fail(
            db,
            f["b_user"],
            f["b"],
            f["hmac"],
            provided=expected_flag(f["a"], "web-jwt"),
        )
        st = anticheat.incidents()
        assert st["incidents"] == [] and st["cursor"] > 0
    destroy_ctfd(app)
