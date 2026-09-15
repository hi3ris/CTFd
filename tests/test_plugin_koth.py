"""King-of-the-Hill scoring plugin.

Runs on SQLite with plugins loaded (no Docker): the hill's HTTP `/king` is
monkeypatched, so these tests pin the plugin's *scoring rules* — token
derivation, who scores, the ctftime/pause gate, freeze on the public board, and
the visibility of the scoreboard holder badge — without ever building a hill.
"""
import importlib
import json
import os

from CTFd.models import Awards
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_team,
    login_as_user,
    register_user,
    setup_ctfd,
)

os.environ.setdefault("CTF_TEAM_FLAG_SECRET", "test-secret")

HILLS = json.dumps(
    [
        {
            "id": "throne",
            "name": "The Throne",
            "url": "http://hill:8080",
            "player_url": "http://ctf/throne",
            "points": 5,
        }
    ]
)


def _koth(monkeypatch, **env):
    """(Re)load the plugin's settings + module against a given environment.

    settings reads os.environ at call time, so setting the vars is enough; we
    reload the package so is_active()/hills() see them and reset module caches.
    """
    for k, v in {
        "KOTH_SCORER_SECRET": "s3cr3t",
        "KOTH_GLOBAL_SECRET": "g10bal",
        "KOTH_HILLS": HILLS,
        "KOTH_TICK": "30",
    }.items():
        monkeypatch.setenv(k, env.pop(k, v))
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    from CTFd.plugins.koth import settings as koth_settings

    importlib.reload(koth_settings)
    import CTFd.plugins.koth as koth

    importlib.reload(koth)
    return koth


def _teams_app():
    app = create_ctfd(enable_plugins=True, setup=False)
    return setup_ctfd(app, user_mode="teams", ctf_theme="hibris", ctf_name="NCTF26")


def _king_of(koth, hill_id, account_id, ts):
    """A fake /king response planting `account_id`'s token, stamped at `ts`."""
    tok = koth.koth_token_for(account_id, hill_id)
    return {"token": tok, "ts": ts}


def _drop_awards(koth):
    """A fake /king that leaves the throne vacant (no valid claim)."""
    return {"token": "", "ts": 0}


def test_token_is_unique_and_resolves(monkeypatch):
    koth = _koth(monkeypatch)
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db

        t1 = gen_team(db, name="alpha", email="a@x.com")
        t2 = gen_team(db, name="bravo", email="b@x.com")
        tok1 = koth.koth_token_for(t1.id, "throne")
        tok2 = koth.koth_token_for(t2.id, "throne")
        assert tok1 != tok2
        assert len(tok1) == 16
        # per-hill: same team, different hill -> different token
        assert koth.koth_token_for(t1.id, "citadel") != tok1
        assert koth._resolve(tok1, "throne")[0] == t1.id
        assert koth._resolve("deadbeef", "throne") is None
    destroy_ctfd(app)


def test_hills_parse_and_scorer_secret_override(monkeypatch):
    koth = _koth(
        monkeypatch,
        KOTH_HILLS=json.dumps(
            [
                {"id": "a", "url": "http://a:8080", "points": 5},
                {
                    "id": "b",
                    "url": "http://b:8081",
                    "points": 9,
                    "scorer_secret": "own",
                },
                {"id": "", "url": "http://bad"},  # dropped: no id
            ]
        ),
    )
    hills = koth.settings.hills()
    assert [h["id"] for h in hills] == ["a", "b"]
    assert hills[0]["scorer_secret"] == "s3cr3t"  # falls back to global
    assert hills[1]["scorer_secret"] == "own"  # per-hill override
    assert koth.settings.is_active() is True


def test_holder_scores_each_tick(monkeypatch):
    import time as _t

    koth = _koth(monkeypatch)
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db

        tid = gen_team(db, name="alpha", email="a@x.com").id
        monkeypatch.setattr(
            koth, "_poll_king", lambda h: _king_of(koth, h["id"], tid, _t.time())
        )
        koth._score_once(app)
        koth._score_once(app)
        awards = Awards.query.filter_by(team_id=tid).all()
        assert len(awards) == 2
        assert awards[0].value == 5
        assert awards[0].category == "koth:throne"
        assert len(awards[0].name) <= 80
    destroy_ctfd(app)


def test_user_level_hold_scores_half(monkeypatch):
    """A boot2root hill held only at user level ('level': 'user') awards half
    the points, floored at 1; root and a level-less hill (Throne) award full."""
    import time as _t

    koth = _koth(
        monkeypatch,
        KOTH_HILLS=json.dumps([{"id": "b2r", "url": "http://h:8082", "points": 5}]),
    )
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db

        tid = gen_team(db, name="alpha", email="a@x.com").id

        def king(level):
            k = _king_of(koth, "b2r", tid, _t.time())
            k["level"] = level
            return k

        # user hold -> half (5 // 2 = 2)
        monkeypatch.setattr(koth, "_poll_king", lambda h: king("user"))
        koth._score_once(app)
        # root hold -> full
        monkeypatch.setattr(koth, "_poll_king", lambda h: king("root"))
        koth._score_once(app)
        # no level reported (Throne/Citadel) -> full
        monkeypatch.setattr(
            koth, "_poll_king", lambda h: _king_of(koth, "b2r", tid, _t.time())
        )
        koth._score_once(app)
        values = sorted(a.value for a in Awards.query.filter_by(team_id=tid).all())
        assert values == [2, 5, 5]

        # the level surfaces in the hill view for the page/badge
        snap = koth.get_snapshot({"id": "b2r", "url": "http://h:8082"})
        view = koth._hill_view({"id": "b2r"}, snap, _t.time())
        assert view["level"] == "root"
    destroy_ctfd(app)


def test_no_score_when_stale_or_unknown_or_offline(monkeypatch):
    import time as _t

    koth = _koth(monkeypatch, KOTH_FRESH_WINDOW="60")
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db

        tid = gen_team(db, name="alpha", email="a@x.com").id

        # stale claim (ts far in the past) -> no award
        monkeypatch.setattr(
            koth, "_poll_king", lambda h: _king_of(koth, h["id"], tid, _t.time() - 999)
        )
        koth._score_once(app)
        assert Awards.query.count() == 0

        # unknown token -> no award
        monkeypatch.setattr(
            koth, "_poll_king", lambda h: {"token": "ffffffffffffffff", "ts": _t.time()}
        )
        koth._score_once(app)
        assert Awards.query.count() == 0

        # hill offline (poll raises) -> no award
        def _boom(h):
            raise OSError("down")

        monkeypatch.setattr(koth, "_poll_king", _boom)
        koth._score_once(app)
        assert Awards.query.count() == 0
    destroy_ctfd(app)


def test_no_score_outside_ctftime_or_when_paused(monkeypatch):
    import time as _t

    koth = _koth(monkeypatch)
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db
        from CTFd.utils import set_config

        tid = gen_team(db, name="alpha", email="a@x.com").id
        monkeypatch.setattr(
            koth, "_poll_king", lambda h: _king_of(koth, h["id"], tid, _t.time())
        )

        # CTF ends in the past -> ctftime() False -> no award
        set_config("start", int(_t.time()) - 1000)
        set_config("end", int(_t.time()) - 500)
        koth._score_once(app)
        assert Awards.query.count() == 0

        # inside the window but paused -> no award
        set_config("end", int(_t.time()) + 5000)
        set_config("paused", True)
        koth._score_once(app)
        assert Awards.query.count() == 0

        # running and not paused -> scores
        set_config("paused", False)
        koth._score_once(app)
        assert Awards.query.count() == 1
    destroy_ctfd(app)


def test_leaderboard_honours_freeze_for_non_admin(monkeypatch):
    import datetime
    import time as _t

    koth = _koth(monkeypatch)
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db
        from CTFd.utils import set_config

        team = gen_team(db, name="alpha", email="a@x.com")
        tid, tname = team.id, team.name
        # two awards, one before and one after the freeze instant
        freeze = int(_t.time())
        before = Awards(
            team_id=tid,
            category="koth:throne",
            value=5,
            date=datetime.datetime.utcfromtimestamp(freeze - 100),
        )
        after = Awards(
            team_id=tid,
            category="koth:throne",
            value=5,
            date=datetime.datetime.utcfromtimestamp(freeze + 100),
        )
        db.session.add_all([before, after])
        db.session.commit()
        set_config("freeze", freeze)

        name_by_id = {tid: tname}
        public = koth._leaderboard("throne", name_by_id, admin=False)
        admin = koth._leaderboard("throne", name_by_id, admin=True)
        assert public[0]["score"] == 5  # only the pre-freeze award
        assert admin[0]["score"] == 10  # admin sees both
    destroy_ctfd(app)


def test_holders_endpoint_hidden_under_freeze(monkeypatch):
    import time as _t

    koth = _koth(monkeypatch)
    app = _teams_app()
    with app.app_context():
        from CTFd.models import db
        from CTFd.utils import set_config

        tid = gen_team(db, name="alpha", email="a@x.com").id
        register_user(app)
        monkeypatch.setattr(
            koth, "_poll_king", lambda h: _king_of(koth, h["id"], tid, _t.time())
        )
        koth._score_once(app)  # publishes the snapshot (holder = team)

        client = login_as_user(app)
        r = client.get("/plugins/koth/api/holders")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert any(d["account_id"] == tid for d in data)

        # freeze the scoreboard -> holders hidden from non-admin
        set_config("freeze", int(_t.time()) - 10)
        r = client.get("/plugins/koth/api/holders")
        assert r.get_json()["data"] == []
    destroy_ctfd(app)


def test_player_page_renders_with_navbar(monkeypatch):
    _koth(monkeypatch)
    app = _teams_app()
    with app.app_context():
        register_user(app)
        client = login_as_user(app)
        r = client.get("/plugins/koth/")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "King of the Hill" in html
        assert "family=Tourney" in html  # hibris base loaded (navbar/fonts present)
        assert "/plugins/koth/api/state" in html
    destroy_ctfd(app)
