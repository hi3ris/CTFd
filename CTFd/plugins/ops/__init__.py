"""Ops dashboard -- one admin page to see in three seconds whether something
is burning during the event, instead of juggling `make logs`, `make gpu`, the
KotH admin page and the CTFd admin.

Read-only, like the KotH page: no action, no button that changes state.

Sections of GET /plugins/ops/api/status (admins only, also meant for a
secondary screen):

  time         ctftime / paused / frozen / remaining
  players      accounts, "active" = acted (POST/PATCH/PUT/DELETE or new IP)
               in the last 15 min -- that is what CTFd's Tracking records;
               teams with >= 1 solve
  submissions  per-minute buckets over the last hour (correct / incorrect /
               ratelimited), top 5 most attempted challenges in the hour
  http         requests and 5xx per minute over the last 10 min, counted by an
               after_request hook. "5xx Flask" only: a gunicorn timeout or an
               unhandled exception that never reaches a response is not seen.
  instancer    live instances / capacity (frp port pool), per team, oldest,
               reaper heartbeat, instances in error
  koth         hills online / holder / awarded points (plugin koth)
  firstblood   last first blood (plugin firstblood)
  anticheat    incidents seen so far (plugin anticheat cache, never rescans)
  health       DB ping + size, Redis ping, last automatic backup (status.json
               written by deploy/scripts/backup.sh, mounted read-only)

Cross-plugin imports happen inside the request, guarded: plugins load in
directory order and any of them may be absent; a missing one renders "n/a",
never a 500 on the page that is supposed to tell you what is broken.
"""

import datetime
import json
import os
import time

from flask import Blueprint, jsonify, render_template, request

from CTFd.cache import cache
from CTFd.models import Challenges, Solves, Submissions, Teams, Tracking, Users, db
from CTFd.plugins import register_admin_plugin_menu_bar
from CTFd.utils import get_config
from CTFd.utils.config import is_scoreboard_frozen, is_teams_mode
from CTFd.utils.dates import ctf_ended, ctf_paused, ctf_started, ctftime
from CTFd.utils.decorators import admins_only

bp = Blueprint("ops", __name__, template_folder="templates")

HTTP_KEY = "ops:http:{}:{}"  # minute bucket, all|5xx
HTTP_WINDOW_MIN = 10
ACTIVE_WINDOW = datetime.timedelta(minutes=15)
BACKUP_MAX_AGE_EVENT = 30 * 60
BACKUP_MAX_AGE_IDLE = 7 * 3600


# --------------------------------------------------------------------------
# HTTP counters (after_request hook)
# --------------------------------------------------------------------------
def _bump(key, ttl=(HTTP_WINDOW_MIN + 2) * 60):
    """Increment a counter; Redis INCR when available, get/set otherwise."""
    try:
        cache.inc(key)
        cache.expire(key, ttl)
        return
    except Exception:  # nosec B110 - not Redis (simple/filesystem cache): fall back
        pass
    try:
        cache.set(key, int(cache.get(key) or 0) + 1, timeout=ttl)
    except Exception:  # nosec B110 - counting must never break a response
        pass


def count_response(status_code, minute=None):
    minute = int(minute if minute is not None else time.time() // 60)
    _bump(HTTP_KEY.format(minute, "all"))
    if status_code >= 500:
        _bump(HTTP_KEY.format(minute, "5xx"))


def http_stats(now=None):
    now = int((now if now is not None else time.time()) // 60)
    buckets = []
    for m in range(now - HTTP_WINDOW_MIN + 1, now + 1):
        buckets.append(
            {
                "minute": m * 60,
                "all": int(cache.get(HTTP_KEY.format(m, "all")) or 0),
                "5xx": int(cache.get(HTTP_KEY.format(m, "5xx")) or 0),
            }
        )
    total = sum(b["all"] for b in buckets)
    errors = sum(b["5xx"] for b in buckets)
    return {
        "window_min": HTTP_WINDOW_MIN,
        "requests": total,
        "errors_5xx": errors,
        "error_rate": round(errors / total, 4) if total else 0.0,
        "per_minute": buckets,
    }


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
def _sec_time(now):
    end = get_config("end")
    return {
        "started": ctf_started(),
        "ended": ctf_ended(),
        "ctftime": ctftime(),
        "paused": ctf_paused(),
        "frozen": is_scoreboard_frozen(),
        "remaining_seconds": max(0, int(int(end) - now)) if end else None,
        "start": get_config("start"),
        "freeze": get_config("freeze"),
        "end": get_config("end"),
    }


def _sec_players(now_dt):
    teams = is_teams_mode()
    active_users = (
        db.session.query(db.func.count(db.func.distinct(Tracking.user_id)))
        .filter(Tracking.date >= now_dt - ACTIVE_WINDOW)
        .scalar()
        or 0
    )
    out = {
        "mode": "teams" if teams else "users",
        "users": Users.query.filter_by(hidden=False, banned=False).count(),
        "active_15min": int(active_users),
        "active_note": "ont agi (soumission, connexion, nouvelle IP) dans les 15 min",
    }
    if teams:
        out["teams"] = Teams.query.filter_by(hidden=False, banned=False).count()
        out["teams_with_solve"] = (
            db.session.query(db.func.count(db.func.distinct(Solves.team_id)))
            .filter(Solves.team_id.isnot(None))
            .scalar()
            or 0
        )
    else:
        out["users_with_solve"] = (
            db.session.query(db.func.count(db.func.distinct(Solves.user_id))).scalar()
            or 0
        )
    return out


def _sec_submissions(now_dt):
    since = now_dt - datetime.timedelta(hours=1)
    rows = (
        db.session.query(Submissions.type, Submissions.date, Submissions.challenge_id)
        .filter(Submissions.date >= since)
        .all()
    )
    per_min = {}
    by_chal = {}
    totals = {"correct": 0, "incorrect": 0, "ratelimited": 0, "other": 0}
    for typ, date, cid in rows:
        key = typ if typ in totals else "other"
        totals[key] += 1
        m = int(date.replace(second=0, microsecond=0).timestamp())
        b = per_min.setdefault(m, {"correct": 0, "incorrect": 0, "ratelimited": 0})
        if typ in b:
            b[typ] += 1
        by_chal[cid] = by_chal.get(cid, 0) + 1
    top_ids = sorted(by_chal, key=by_chal.get, reverse=True)[:5]
    names = (
        dict(
            Challenges.query.with_entities(Challenges.id, Challenges.name)
            .filter(Challenges.id.in_(top_ids))
            .all()
        )
        if top_ids
        else {}
    )
    last10 = [
        b
        for m, b in per_min.items()
        if m >= int((now_dt - datetime.timedelta(minutes=10)).timestamp())
    ]
    return {
        "last_hour": totals,
        "per_min_last10": round(sum(sum(b.values()) for b in last10) / 10.0, 1),
        "per_minute": [{"minute": m, **per_min[m]} for m in sorted(per_min)],
        "top_attempted": [
            {"challenge_id": cid, "name": names.get(cid, "?"), "attempts": by_chal[cid]}
            for cid in top_ids
        ],
    }


def _sec_instancer(now_dt):
    try:
        from CTFd.plugins.team_instancer import settings as inst_settings
        from CTFd.plugins.team_instancer.models import FrpPort, TeamInstance
    except Exception as e:  # plugin absent or not importable here
        return {"available": False, "error": e.__class__.__name__}
    try:
        by_status = dict(
            db.session.query(TeamInstance.status, db.func.count(TeamInstance.id))
            .group_by(TeamInstance.status)
            .all()
        )
        total_ports = FrpPort.query.count()
        used_ports = FrpPort.query.filter(FrpPort.instance_id.isnot(None)).count()
        oldest = db.session.query(db.func.min(TeamInstance.start_time)).scalar()
        per_team = (
            db.session.query(TeamInstance.account_id, db.func.count(TeamInstance.id))
            .group_by(TeamInstance.account_id)
            .order_by(db.func.count(TeamInstance.id).desc())
            .limit(5)
            .all()
        )
        names = {}
        if per_team:
            Model = Teams if is_teams_mode() else Users
            names = dict(
                Model.query.with_entities(Model.id, Model.name)
                .filter(Model.id.in_([t[0] for t in per_team]))
                .all()
            )
        last_reap = cache.get("instancer:last_reap")
        reap_age = int(time.time() - last_reap) if last_reap else None
        errors = (
            TeamInstance.query.filter_by(status="error")
            .order_by(TeamInstance.created_at.desc())
            .limit(5)
            .all()
        )
        return {
            "available": True,
            "active": bool(inst_settings.is_active()),
            "live": int(sum(by_status.values())),
            "by_status": {k: int(v) for k, v in by_status.items()},
            "capacity": int(total_ports),
            "ports_used": int(used_ports),
            "oldest_age_seconds": int((now_dt - oldest).total_seconds())
            if oldest
            else None,
            "ttl_seconds": int(getattr(inst_settings, "INSTANCE_TTL", 0) or 0),
            "reaper_age_seconds": reap_age,
            "reaper_ok": bool(
                reap_age is not None
                and reap_age
                <= 3 * int(getattr(inst_settings, "REAP_INTERVAL", 60) or 60)
            ),
            "per_team": [
                {"account_id": a, "name": names.get(a, "#%s" % a), "instances": int(n)}
                for a, n in per_team
            ],
            "errors": [
                {
                    "account_id": e.account_id,
                    "challenge_id": e.challenge_id,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in errors
            ],
        }
    except Exception as e:  # table missing (migration not run) etc.
        db.session.rollback()
        return {"available": False, "error": e.__class__.__name__}


def _sec_koth():
    try:
        from CTFd.plugins import koth
        from CTFd.plugins.koth import settings as koth_settings
    except Exception as e:
        return {"available": False, "error": e.__class__.__name__}
    try:
        if not koth_settings.is_active():
            return {"available": True, "active": False, "hills": []}
        hills = []
        for h in koth_settings.hills():
            snap = koth.get_snapshot(h, live_fallback=False) or {}
            king = snap.get("king") or {}
            hills.append(
                {
                    "id": h["id"],
                    "name": h["name"],
                    "online": bool(king.get("online", snap.get("online"))),
                    "holder": king.get("holder") or snap.get("holder"),
                    "fresh": bool(king.get("fresh", snap.get("fresh"))),
                    "error": snap.get("error"),
                    "points": h.get("points"),
                }
            )
        last_tick = cache.get("koth:last_tick")
        return {
            "available": True,
            "active": True,
            "scoring": bool(koth.scoring_open()),
            "last_tick_age": int(time.time() - last_tick) if last_tick else None,
            "hills": hills,
        }
    except Exception as e:
        return {"available": False, "error": e.__class__.__name__}


def _sec_firstblood():
    try:
        from CTFd.plugins import firstblood
    except Exception as e:
        return {"available": False, "error": e.__class__.__name__}
    try:
        rows = firstblood.first_solves(limit=1)
        last = rows[0] if rows else None
        return {
            "available": True,
            "last": {
                "name": last["name"],
                "challenge": last["challenge"],
                "category": last["category"],
                "date": last["date"].isoformat() if last["date"] else None,
            }
            if last
            else None,
        }
    except Exception as e:
        db.session.rollback()
        return {"available": False, "error": e.__class__.__name__}


def _sec_anticheat():
    try:
        from CTFd.plugins import anticheat
    except Exception as e:
        return {"available": False, "error": e.__class__.__name__}
    state = cache.get(anticheat.CACHE_KEY)
    if not isinstance(state, dict):
        return {"available": True, "scanned": False, "incidents": 0}
    inc = state.get("incidents") or []
    return {
        "available": True,
        "scanned": True,
        "incidents": len(inc),
        "pairs": len({(i.get("submitter_id"), i.get("owner_id")) for i in inc}),
        "last": inc[-1]["date"] if inc else None,
    }


def _db_size_bytes():
    dialect = db.engine.dialect.name
    try:
        if dialect in ("mysql", "mariadb"):
            return int(
                db.session.execute(
                    db.text(
                        "SELECT COALESCE(SUM(data_length + index_length), 0) "
                        "FROM information_schema.tables WHERE table_schema = DATABASE()"
                    )
                ).scalar()
                or 0
            )
        if dialect == "postgresql":
            return int(
                db.session.execute(
                    db.text("SELECT pg_database_size(current_database())")
                ).scalar()
                or 0
            )
        if dialect == "sqlite":
            path = db.engine.url.database
            if path and os.path.exists(path):
                return os.path.getsize(path)
            return 0
    except Exception:
        db.session.rollback()
    return None


def backup_status(path=None, now=None, in_event=False):
    """Age of the last successful automatic dump, read from status.json."""
    path = path or os.environ.get("BACKUP_STATUS_FILE", "/backups/status.json")
    now = now if now is not None else time.time()
    if not os.path.exists(path):
        return {"available": False, "ok": False, "reason": "status.json absent"}
    try:
        with open(path) as fh:
            d = json.load(fh)
    except Exception as e:
        return {"available": False, "ok": False, "reason": e.__class__.__name__}
    last_ok = int(d.get("last_ok") or 0)
    age = int(now - last_ok) if last_ok else None
    max_age = BACKUP_MAX_AGE_EVENT if in_event else BACKUP_MAX_AGE_IDLE
    return {
        "available": True,
        "ok": bool(age is not None and age <= max_age and d.get("ok", True)),
        "age_seconds": age,
        "max_age_seconds": max_age,
        "last_run_age": int(now - int(d.get("last_run") or 0))
        if d.get("last_run")
        else None,
        "last_ok_file": d.get("file"),
        "size": d.get("size"),
        "s3": d.get("s3"),
        "kind": d.get("kind"),
        "error": d.get("error") or "",
    }


def _sec_health(in_event):
    out = {}
    t0 = time.time()
    try:
        db.session.execute(db.text("SELECT 1"))
        out["db"] = {"ok": True, "ping_ms": round((time.time() - t0) * 1000, 1)}
    except Exception as e:
        db.session.rollback()
        out["db"] = {"ok": False, "error": e.__class__.__name__}
    out["db"]["dialect"] = db.engine.dialect.name
    out["db"]["size_bytes"] = _db_size_bytes()
    try:
        client = getattr(cache.cache, "_write_client", None)
        if client is not None:
            t0 = time.time()
            client.ping()
            out["redis"] = {"ok": True, "ping_ms": round((time.time() - t0) * 1000, 1)}
        else:
            out["redis"] = {
                "ok": None,
                "note": "cache non Redis (%s)" % cache.cache.__class__.__name__,
            }
    except Exception as e:
        out["redis"] = {"ok": False, "error": e.__class__.__name__}
    out["backup"] = backup_status(in_event=in_event)
    return out


def status():
    now = time.time()
    now_dt = datetime.datetime.utcnow()
    t = _sec_time(now)
    return {
        "generated_at": int(now),
        "time": t,
        "players": _sec_players(now_dt),
        "submissions": _sec_submissions(now_dt),
        "http": http_stats(now),
        "instancer": _sec_instancer(now_dt),
        "koth": _sec_koth(),
        "firstblood": _sec_firstblood(),
        "anticheat": _sec_anticheat(),
        "health": _sec_health(in_event=bool(t["ctftime"])),
        "render_ms": round((time.time() - now) * 1000, 1),
    }


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
@bp.route("/api/status")
@admins_only
def api_status():
    return jsonify({"success": True, "data": status()})


@bp.route("/admin")
@admins_only
def admin_page():
    return render_template("ops/admin.html")


def load(app):
    app.register_blueprint(bp, url_prefix="/plugins/ops")
    register_admin_plugin_menu_bar("Ops", "/plugins/ops/admin")

    @app.after_request
    def _ops_count(response):
        # Skip our own polling so the dashboard does not count itself.
        if not request.path.startswith("/plugins/ops/"):
            count_response(response.status_code)
        return response
