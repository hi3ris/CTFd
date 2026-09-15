"""First blood announcer.

"🩸 First blood — Kékéli Defenders ouvre heap-note (pwn)" projected in the
room is what makes ten teams jump. CTFd already has Notifications (SSE to the
navbar, toast rendered by the hibris theme), so the plugin only has to notice
the first solve of each challenge and post one.

  * A first blood is the EARLIEST Solves row of a challenge by an account that
    is neither hidden nor banned (same semantics as get_standings): an
    organiser's hidden test team must not steal the announcement.
  * A light loop (same pattern as the KotH scorer: fcntl lock so one gunicorn
    worker runs it, never started under TESTING) polls every FIRSTBLOOD_TICK
    seconds. The set of announced challenges lives in the cache; on a cold
    cache it is SEEDED from the existing first solves without posting, so a
    redeploy does not replay history into the room. A solve landing between
    that seed and the first real tick is marked silently -- accepted.
  * Scoreboard freeze: after `freeze` nothing is posted publicly (the freeze
    only lifts at the end); the public `recent` feed hides post-freeze entries
    for non-admins, admins see everything.
  * FIRSTBLOOD_BONUS (points, default 0 = off) inserts an Awards row per first
    blood (category "firstblood"). Off unless the règlement says otherwise.
  * `GET /plugins/firstblood/api/recent` is read straight from Solves (not the
    loop's memory), so the HUD segment and the Grand Prix ticker survive
    restarts and never depend on the announcer having run.
"""

import fcntl
import os
import threading
import time

from flask import Blueprint, current_app, jsonify, request

from CTFd.cache import cache, clear_standings
from CTFd.models import Awards, Challenges, Notifications, Solves, db
from CTFd.schemas.notifications import NotificationSchema
from CTFd.utils import get_config
from CTFd.utils.config import is_scoreboard_frozen, is_teams_mode
from CTFd.utils.dates import unix_time_to_utc
from CTFd.utils.decorators import ratelimit
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_score_visibility,
)
from CTFd.utils.modes import get_model
from CTFd.utils.user import is_admin

bp = Blueprint("firstblood", __name__)

_LOCK_PATH = "/tmp/ctfd_firstblood.lock"  # nosec B108 - lock file, not data
ANNOUNCED_KEY = "firstblood:announced"  # {challenge_id: solve_id}
RECENT_KEY = "firstblood:recent:{}"
TITLE = "🩸 First blood"
AWARD_CATEGORY = "firstblood"
_AWARD_NAME_MAX = 80


def tick_seconds():
    try:
        return max(2, int(os.environ.get("FIRSTBLOOD_TICK", "5")))
    except ValueError:
        return 5


def bonus_points():
    try:
        return max(0, int(os.environ.get("FIRSTBLOOD_BONUS", "0") or 0))
    except ValueError:
        return 0


# --------------------------------------------------------------------------
# Query
# --------------------------------------------------------------------------
def first_solves(before=None, limit=None):
    """Earliest solve per visible challenge by a visible, unbanned account.

    Newest first. `before` (datetime) drops later solves -- used to honour the
    scoreboard freeze for the public feed.
    """
    Model = get_model()
    col = Solves.team_id if is_teams_mode() else Solves.user_id
    valid = (
        db.session.query(
            Solves.challenge_id.label("cid"), db.func.min(Solves.id).label("sid")
        )
        .join(Model, col == Model.id)
        .join(Challenges, Challenges.id == Solves.challenge_id)
        .filter(
            Model.hidden == False,  # noqa: E712
            Model.banned == False,  # noqa: E712
            Challenges.state == "visible",
        )
    )
    if before is not None:
        valid = valid.filter(Solves.date <= before)
    valid = valid.group_by(Solves.challenge_id).subquery()

    q = (
        db.session.query(
            Solves.id,
            Solves.challenge_id,
            Challenges.name,
            Challenges.category,
            col,
            Model.name,
            Solves.user_id,
            Solves.team_id,
            Solves.date,
        )
        .join(valid, Solves.id == valid.c.sid)
        .join(Challenges, Challenges.id == Solves.challenge_id)
        .join(Model, col == Model.id)
        .order_by(Solves.date.desc(), Solves.id.desc())
    )
    if limit:
        q = q.limit(limit)
    return [
        {
            "solve_id": r[0],
            "challenge_id": r[1],
            "challenge": r[2],
            "category": r[3],
            "account_id": r[4],
            "name": r[5],
            "user_id": r[6],
            "team_id": r[7],
            "date": r[8],
        }
        for r in q.all()
    ]


# --------------------------------------------------------------------------
# Announce
# --------------------------------------------------------------------------
def _post_notification(fb):
    n = Notifications(
        title=TITLE,
        content="{} ouvre {} ({})".format(fb["name"], fb["challenge"], fb["category"]),
    )
    db.session.add(n)
    db.session.commit()
    data = NotificationSchema().dump(n).data
    data["type"] = "toast"
    data["sound"] = True
    current_app.events_manager.publish(data=data, type="notification")
    return n


def _award(fb, points):
    db.session.add(
        Awards(
            user_id=fb["user_id"],
            team_id=fb["team_id"],
            name=("🩸 First blood — " + fb["challenge"])[:_AWARD_NAME_MAX],
            description="Première équipe à résoudre {}".format(fb["challenge"]),
            value=points,
            category=AWARD_CATEGORY,
            icon="medal",
        )
    )


def announce_once():
    """One pass: post a notification for every first blood not yet announced.
    Returns the list of first bloods announced PUBLICLY (empty under freeze).
    """
    fresh = first_solves()
    seen = cache.get(ANNOUNCED_KEY)
    if not isinstance(seen, dict):
        # Cold cache (first start, redis restart): seed silently, never replay.
        cache.set(
            ANNOUNCED_KEY, {s["challenge_id"]: s["solve_id"] for s in fresh}, timeout=0
        )
        return []
    new = [s for s in fresh if s["challenge_id"] not in seen]
    if not new:
        return []
    bonus = bonus_points()
    frozen = is_scoreboard_frozen()
    posted = []
    for fb in sorted(new, key=lambda s: s["solve_id"]):
        seen[fb["challenge_id"]] = fb["solve_id"]
        if bonus:
            _award(fb, bonus)
        if not frozen:
            _post_notification(fb)
            posted.append(fb)
    db.session.commit()
    if bonus:
        clear_standings()
    cache.set(ANNOUNCED_KEY, seen, timeout=0)
    for admin in ("1", "0"):
        cache.delete(RECENT_KEY.format(admin))
    return posted


def _loop(app):
    lock_file = open(_LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return  # another worker announces
    while True:
        try:
            with app.app_context():
                announce_once()
        except Exception:  # nosec B110 - the loop must survive a bad pass
            try:
                db.session.rollback()
            except Exception:  # nosec B110
                pass
        time.sleep(tick_seconds())


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
@bp.route("/api/recent")
@check_account_visibility
@check_score_visibility
@ratelimit(method="GET", limit=120, interval=60)
def api_recent():
    try:
        limit = min(20, max(1, int(request.args.get("limit", 5))))
    except ValueError:
        limit = 5
    admin = is_admin()
    key = RECENT_KEY.format("1" if admin else "0")
    rows = cache.get(key)
    if rows is None:
        before = None
        if not admin and is_scoreboard_frozen():
            before = unix_time_to_utc(int(get_config("freeze")))
        rows = [
            {
                "solve_id": s["solve_id"],
                "challenge_id": s["challenge_id"],
                "challenge": s["challenge"],
                "category": s["category"],
                "account_id": s["account_id"],
                "name": s["name"],
                "date": s["date"].isoformat() if s["date"] else None,
            }
            for s in first_solves(before=before, limit=20)
        ]
        cache.set(key, rows, timeout=10)
    return jsonify(
        {
            "success": True,
            "data": rows[:limit],
            "frozen": bool(is_scoreboard_frozen() and not admin),
        }
    )


def load(app):
    app.register_blueprint(bp, url_prefix="/plugins/firstblood")
    enabled = os.environ.get("FIRSTBLOOD_ENABLED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )
    if enabled and not app.config.get("TESTING"):
        t = threading.Thread(target=_loop, args=(app,), daemon=True)
        t.start()
