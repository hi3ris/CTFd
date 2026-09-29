"""Ops dashboard (plugins/ops): admin-only status JSON with every section,
HTTP counters from the after_request hook, backup status ageing, and a
render time that stays well under a second on the test app.
"""
import json
import os
import time

from CTFd.plugins import ops
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_challenge,
    gen_fail,
    gen_solve,
    gen_team,
    login_as_user,
    setup_ctfd,
)

SECTIONS = {
    "time",
    "players",
    "submissions",
    "http",
    "instancer",
    "koth",
    "firstblood",
    "anticheat",
    "health",
}


def _app():
    app = create_ctfd(enable_plugins=True, setup=False)
    return setup_ctfd(app, user_mode="teams", ctf_theme="hibris", ctf_name="NCTF26")


def test_status_admin_only_and_complete():
    app = _app()
    with app.app_context():
        from CTFd.models import db

        a = gen_team(db, name="alpha", email="a@x.com")
        a_user, a_id, a_login = a.members[0].id, a.id, a.members[0].name
        c = gen_challenge(db, name="heap-note", category="pwn").id
        gen_solve(db, a_user, a_id, c)
        gen_fail(db, a_user, a_id, c, provided="nope")

        player = login_as_user(app, name=a_login, password="password")
        r = player.get("/plugins/ops/api/status", content_type="application/json")
        assert r.status_code == 403
        r = player.get("/plugins/ops/admin")
        assert r.status_code == 302

        admin = login_as_user(app, name="admin", password="password")
        t0 = time.time()
        r = admin.get("/plugins/ops/api/status")
        assert r.status_code == 200
        assert time.time() - t0 < 1.0
        d = r.get_json()["data"]
        assert SECTIONS <= set(d)
        assert d["players"]["mode"] == "teams"
        assert d["players"]["teams_with_solve"] == 1
        assert d["players"]["active_15min"] >= 1  # the login itself is tracked
        assert d["submissions"]["last_hour"] == {
            "correct": 1,
            "incorrect": 1,
            "ratelimited": 0,
            "other": 0,
        }
        assert d["submissions"]["top_attempted"][0]["name"] == "heap-note"
        assert d["health"]["db"]["ok"] is True
        assert d["health"]["db"]["dialect"]
        assert d["health"]["backup"]["available"] is False  # no status.json in tests
        assert d["instancer"]["available"] is True
        assert d["instancer"]["live"] == 0 and d["instancer"]["active"] is False
        assert d["koth"]["available"] is True
        assert d["firstblood"]["last"]["challenge"] == "heap-note"
        assert d["anticheat"]["available"] is True
        assert d["render_ms"] < 1000

        r = admin.get("/plugins/ops/admin")
        assert r.status_code == 200
        assert "/plugins/ops/api/status" in r.get_data(as_text=True)
    destroy_ctfd(app)


def test_http_counters_and_hook():
    app = create_ctfd(enable_plugins=True, setup=False)

    # Registered before the first request (setup_ctfd already makes some):
    # Flask refuses routes added later.
    @app.route("/ops-test-500")
    def _boom():
        return "boom", 500

    app = setup_ctfd(app, user_mode="teams", ctf_theme="hibris", ctf_name="NCTF26")
    with app.app_context():
        ops.cache.clear()
        minute = 1_000_000
        ops.count_response(200, minute)
        ops.count_response(500, minute)
        ops.count_response(503, minute)
        st = ops.http_stats(now=minute * 60 + 30)
        assert st["requests"] == 3 and st["errors_5xx"] == 2
        assert st["error_rate"] == round(2 / 3, 4)
        assert st["per_minute"][-1]["minute"] == minute * 60

        # the hook counts real responses (a 404 counts as a request, not 5xx)
        ops.cache.clear()
        admin = login_as_user(app, name="admin", password="password")
        admin.get("/this-does-not-exist")
        admin.get("/plugins/ops/api/status")  # excluded: never counts itself
        st = ops.http_stats()
        assert st["requests"] >= 1 and st["errors_5xx"] == 0

        admin.get("/ops-test-500")
        assert ops.http_stats()["errors_5xx"] == 1
    destroy_ctfd(app)


def test_backup_status_ages(tmp_path):
    p = tmp_path / "status.json"
    now = 2_000_000
    assert ops.backup_status(str(p), now=now)["available"] is False
    p.write_text(
        json.dumps(
            {
                "last_ok": now - 600,
                "last_run": now - 60,
                "ok": True,
                "file": "x",
                "size": 1,
                "s3": True,
                "kind": "sql",
            }
        )
    )
    st = ops.backup_status(str(p), now=now, in_event=True)
    assert st["ok"] is True and st["age_seconds"] == 600 and st["s3"] is True
    p.write_text(
        json.dumps(
            {"last_ok": now - 2000, "last_run": now - 60, "ok": False, "error": "S3"}
        )
    )
    st = ops.backup_status(str(p), now=now, in_event=True)
    assert st["ok"] is False and st["error"] == "S3"
    # the same age is fine outside the event (7 h tolerance)
    p.write_text(json.dumps({"last_ok": now - 2000, "last_run": now - 60, "ok": True}))
    assert ops.backup_status(str(p), now=now, in_event=False)["ok"] is True
    assert ops.backup_status(str(p), now=now, in_event=True)["ok"] is False
    p.write_text("not json")
    assert ops.backup_status(str(p), now=now)["available"] is False
    os.environ["BACKUP_STATUS_FILE"] = str(p)
    try:
        assert ops.backup_status(now=now)["available"] is False
    finally:
        del os.environ["BACKUP_STATUS_FILE"]
