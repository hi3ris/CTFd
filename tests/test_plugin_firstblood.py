"""First blood announcer (plugins/firstblood).

Pins: first valid solve -> one public Notification; later solvers -> nothing;
hidden/banned accounts never take a first blood; nothing public under the
scoreboard freeze (admins still see the feed); optional bonus award.
"""
import calendar
import time

from CTFd.models import Awards, Notifications
from CTFd.plugins import firstblood as fb
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_challenge,
    gen_solve,
    gen_team,
    login_as_user,
    set_config,
    setup_ctfd,
)


def _app():
    app = create_ctfd(enable_plugins=True, setup=False)
    return setup_ctfd(app, user_mode="teams", ctf_theme="hibris", ctf_name="NCTF26")


def _teams(db):
    a = gen_team(db, name="alpha", email="a@x.com")
    b = gen_team(db, name="bravo", email="b@x.com")
    h = gen_team(db, name="ghost", email="g@x.com", hidden=True)
    return (
        {"id": a.id, "user": a.members[0].id, "login": a.members[0].name},
        {"id": b.id, "user": b.members[0].id, "login": b.members[0].name},
        {"id": h.id, "user": h.members[0].id},
    )


def _seed():
    fb.cache.delete(fb.ANNOUNCED_KEY)
    assert fb.announce_once() == []  # cold cache: seeded silently


def test_first_solve_announced_once(monkeypatch):
    monkeypatch.delenv("FIRSTBLOOD_BONUS", raising=False)
    app = _app()
    with app.app_context():
        from CTFd.models import db

        a, b, _ = _teams(db)
        c1 = gen_challenge(db, name="heap-note", category="pwn").id
        _seed()
        gen_solve(db, a["user"], a["id"], c1)
        posted = fb.announce_once()
        assert [p["name"] for p in posted] == ["alpha"]
        assert Notifications.query.count() == 1
        n = Notifications.query.first()
        assert n.title == fb.TITLE
        assert "alpha" in n.content and "heap-note" in n.content and "pwn" in n.content
        # second solver of the same challenge: nothing
        gen_solve(db, b["user"], b["id"], c1)
        assert fb.announce_once() == []
        assert Notifications.query.count() == 1
        # idempotent
        assert fb.announce_once() == []
        assert Awards.query.count() == 0  # bonus off by default
    destroy_ctfd(app)


def test_hidden_team_never_takes_first_blood(monkeypatch):
    monkeypatch.delenv("FIRSTBLOOD_BONUS", raising=False)
    app = _app()
    with app.app_context():
        from CTFd.models import db

        a, _, h = _teams(db)
        c = gen_challenge(db, name="web-jwt", category="web").id
        hidden_chal = gen_challenge(
            db, name="secret", category="misc", state="hidden"
        ).id
        _seed()
        gen_solve(db, h["user"], h["id"], c)
        assert fb.announce_once() == []  # organisers' hidden team
        gen_solve(db, a["user"], a["id"], hidden_chal)
        assert fb.announce_once() == []  # hidden challenge never announced
        gen_solve(db, a["user"], a["id"], c)
        posted = fb.announce_once()
        assert [(p["name"], p["challenge"]) for p in posted] == [("alpha", "web-jwt")]
    destroy_ctfd(app)


def test_freeze_silences_public_but_bonus_still_awarded(monkeypatch):
    monkeypatch.setenv("FIRSTBLOOD_BONUS", "50")
    app = _app()
    with app.app_context():
        from CTFd.models import db

        a, b, _ = _teams(db)
        c1 = gen_challenge(db, name="early", category="crypto").id
        c2 = gen_challenge(db, name="late", category="crypto").id
        _seed()
        early = gen_solve(db, a["user"], a["id"], c1)
        early_ts = calendar.timegm(early.date.utctimetuple())
        assert len(fb.announce_once()) == 1
        aw = Awards.query.filter_by(category=fb.AWARD_CATEGORY).all()
        assert len(aw) == 1 and aw[0].value == 50 and aw[0].team_id == a["id"]

        # freeze one second after the early solve; the late solve lands >= 1.5 s
        # after it, so it is strictly post-freeze whatever the clock does
        set_config("freeze", early_ts + 1)
        time.sleep(1.5)
        gen_solve(db, b["user"], b["id"], c2)
        assert fb.announce_once() == []  # nothing public under freeze
        assert Notifications.query.count() == 1
        assert Awards.query.filter_by(category=fb.AWARD_CATEGORY).count() == 2
        # and it stays announced (no replay once the freeze is lifted)
        set_config("freeze", None)
        assert fb.announce_once() == []

        # public feed: player sees only pre-freeze, admin sees both
        set_config("freeze", early_ts + 1)
        fb.cache.delete(fb.RECENT_KEY.format("0"))
        fb.cache.delete(fb.RECENT_KEY.format("1"))
        player = login_as_user(app, name=b["login"], password="password")
        r = player.get("/plugins/firstblood/api/recent")
        assert r.status_code == 200
        j = r.get_json()
        assert j["frozen"] is True
        assert [(d["name"], d["challenge"]) for d in j["data"]] == [("alpha", "early")]
        admin = login_as_user(app, name="admin", password="password")
        j = admin.get("/plugins/firstblood/api/recent?limit=2").get_json()
        assert j["frozen"] is False
        assert [d["challenge"] for d in j["data"]] == ["late", "early"]
        assert set(j["data"][0]) >= {
            "solve_id",
            "challenge_id",
            "category",
            "account_id",
            "date",
        }
    destroy_ctfd(app)


def test_recent_feed_reads_solves_not_the_loop():
    app = _app()
    with app.app_context():
        from CTFd.models import db

        a, _, _ = _teams(db)
        c = gen_challenge(db, name="osint-1", category="osint").id
        gen_solve(db, a["user"], a["id"], c)
        # no announce_once() ever called: the feed still works
        client = login_as_user(app, name=a["login"], password="password")
        j = client.get("/plugins/firstblood/api/recent").get_json()
        assert [d["challenge"] for d in j["data"]] == ["osint-1"]
        assert j["data"][0]["account_id"] == a["id"]
    destroy_ctfd(app)


def test_deleted_first_solve_hands_the_blood_to_the_next_team(monkeypatch):
    """Purged load-test accounts (or a removed cheater): the announced solve
    disappears, so the next first solve must be announced, not swallowed."""
    monkeypatch.delenv("FIRSTBLOOD_BONUS", raising=False)
    app = _app()
    with app.app_context():
        from CTFd.models import Solves, db

        a, b, _ = _teams(db)
        c1 = gen_challenge(db, name="heap-note", category="pwn").id
        _seed()
        s1 = gen_solve(db, a["user"], a["id"], c1)
        assert [p["name"] for p in fb.announce_once()] == ["alpha"]
        Solves.query.filter_by(id=s1.id).delete()
        db.session.commit()
        assert fb.announce_once() == []  # nobody solved it any more: silence
        gen_solve(db, b["user"], b["id"], c1)
        assert [p["name"] for p in fb.announce_once()] == ["bravo"]
        assert Notifications.query.count() == 2
        assert fb.announce_once() == []
    destroy_ctfd(app)
