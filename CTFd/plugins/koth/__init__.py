"""King-of-the-Hill scoring plugin.

A KotH is a *shared* service (the "hill") that everyone attacks. Whoever has
planted their team's opaque token as the hill's current "king" earns points on
every scoring tick. There is no flag to submit: points accrue as `Awards`, which
`CTFd.utils.scores.get_standings` already sums into the scoreboard, so the kart
scoreboard reflects a held hill automatically.

Three secrets, deliberately separated (see settings.py):

  * HILL_KEY          lives ONLY on the hill container; authorises a claim. It is
                      the thing players must exploit out of the hill. CTFd never
                      sees it.
  * KOTH_SCORER_SECRET  CTFd -> hill trusted read of /king (X-Scorer-Token). Can
                      be overridden per hill (`scorer_secret` in KOTH_HILLS).
  * KOTH_GLOBAL_SECRET  CTFd-side derivation of each team's opaque hill token.
                      The hill never computes it and cannot map a token to a team;
                      only CTFd can. A player learns only their OWN token.

Flow: a player reads their token from this plugin's page, exploits the hill to
obtain HILL_KEY, then repeatedly signs fresh claims with (token, ts) to keep the
throne. The freshness window (settings.fresh_window) means a single claim decays,
so holding requires continuous re-claiming -- the KotH contest.

Event rules enforced here:

  * Points are only awarded while the CTF is running (`ctftime()`) and not
    paused -- a throne held after the end or before the start scores nothing.
  * The per-hill KotH board honours the scoreboard freeze for non-admins, like
    the main scoreboard (awards are dated, so the freeze applies naturally).
  * The scorer publishes a per-hill snapshot (holder, reign, takeovers, online)
    in CTFd's cache every tick; the player page and the scoreboard badge read
    that snapshot instead of hammering the hill on every request.
"""

import fcntl
import hashlib
import hmac
import json
import threading
import time
import urllib.error
import urllib.request

from flask import Blueprint, jsonify, render_template

from CTFd.cache import cache
from CTFd.models import Awards, Teams, Users, db
from CTFd.plugins import register_admin_plugin_menu_bar, register_user_page_menu_bar
from CTFd.utils import get_config
from CTFd.utils.config import is_scoreboard_frozen, is_teams_mode
from CTFd.utils.dates import ctf_paused, ctftime, unix_time_to_utc
from CTFd.utils.decorators import admins_only, authed_only, ratelimit
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_score_visibility,
)
from CTFd.utils.user import get_current_user, is_admin

from . import settings

bp = Blueprint("koth", __name__, template_folder="templates", static_folder="assets")

_SCORER_LOCK_PATH = "/tmp/ctfd_koth_scorer.lock"  # nosec B108 - lock file, not data
_SNAP_KEY = "koth:snap:{}"
_AWARD_NAME_MAX = 80  # Awards.name is String(80)


# --------------------------------------------------------------------------
# Per-team token derivation
# --------------------------------------------------------------------------
def koth_token_for(account_id, koth_id: str) -> str:
    """The opaque token a team plants on the hill to claim the throne.

    Derived from KOTH_GLOBAL_SECRET so it is unguessable and unique per team AND
    per hill. 16 hex (64 bits) is short enough to paste yet infeasible to guess.
    The hill treats it as an opaque string; only CTFd can map it back to a team.
    """
    return hmac.new(
        settings.global_secret().encode("utf-8"),
        f"koth:{koth_id}:{account_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]


def _accounts():
    """(account_id, name) for every scoring account, honouring the CTF mode.

    Hidden/banned accounts are excluded so they can neither hold nor appear."""
    model = Teams if is_teams_mode() else Users
    rows = []
    for a in model.query.all():
        if getattr(a, "hidden", False) or getattr(a, "banned", False):
            continue
        rows.append((a.id, a.name))
    return rows


def _resolve(token: str, koth_id: str):
    """Map a planted token back to (account_id, name), or None. Constant-time
    per candidate so a timing side-channel cannot enumerate tokens."""
    if not token:
        return None
    for aid, name in _accounts():
        if hmac.compare_digest(koth_token_for(aid, koth_id), token):
            return (aid, name)
    return None


def scoring_open() -> bool:
    """Awards flow only while the event is running and not paused."""
    return ctftime() and not ctf_paused()


# --------------------------------------------------------------------------
# Talking to a hill
# --------------------------------------------------------------------------
def _poll_king(hill: dict) -> dict:
    """Read a hill's current king. Raises on any transport/parse error."""
    url = hill["url"] + "/king"
    if not url.startswith(("http://", "https://")):
        raise ValueError("hill url must be http(s)")
    req = urllib.request.Request(
        url, headers={"X-Scorer-Token": hill.get("scorer_secret") or ""}
    )
    with urllib.request.urlopen(  # nosec B310 - internal arena hill, scheme checked
        req, timeout=settings.http_timeout()
    ) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


# --------------------------------------------------------------------------
# Snapshot: what the scorer last saw on each hill (cached, read by the pages)
# --------------------------------------------------------------------------
def _snapshot_ttl() -> int:
    return max(3 * settings.tick_seconds(), 90)


def _build_snapshot(hill: dict, prev: dict, now: float) -> dict:
    """Poll one hill and fold the result into the previous snapshot: reign
    start and takeover count survive across ticks; an unreachable hill keeps
    its last known holder but is flagged offline."""
    prev = prev or {}
    snap = {
        "token": "",
        "ts": 0.0,
        "holder_id": None,
        "holder_name": None,
        "online": False,
        "error": None,
        "reign_since": prev.get("reign_since"),
        "takeovers": int(prev.get("takeovers") or 0),
        "polled_at": now,
    }
    try:
        king = _poll_king(hill)
    except Exception as e:  # nosec B110 - hill down: report offline, keep going
        snap["error"] = e.__class__.__name__
        snap["token"] = prev.get("token", "")
        snap["ts"] = prev.get("ts", 0.0)
        snap["holder_id"] = prev.get("holder_id")
        snap["holder_name"] = prev.get("holder_name")
        snap["level"] = prev.get("level", "root")
        return snap
    snap["online"] = True
    token = str(king.get("token") or "").strip()
    try:
        ts = float(king.get("ts") or 0)
    except (TypeError, ValueError):
        ts = 0.0
    # A hill may report the access level of the current hold. "root" (or a hill
    # that says nothing, like the Throne/Citadel) scores full points; "user"
    # scores half — a boot2root hill held only at user level, root not reached.
    snap["level"] = (
        "user" if str(king.get("level") or "").strip().lower() == "user" else "root"
    )
    snap["token"], snap["ts"] = token, ts
    holder = _resolve(token, hill["id"]) if token else None
    if holder:
        snap["holder_id"], snap["holder_name"] = holder
    # A different token (or a vacant throne) starts a new reign; a takeover is
    # counted only when a *known* team replaces another known team.
    if token != prev.get("token", ""):
        snap["reign_since"] = now if token else None
        if holder and prev.get("holder_id") is not None:
            snap["takeovers"] += 1
    elif token and not snap["reign_since"]:
        snap["reign_since"] = now
    return snap


def get_snapshot(hill: dict, live_fallback: bool = True) -> dict:
    """Last snapshot the scorer published for a hill. On a cache miss (scorer
    not running, or first tick pending) do one live poll and cache it briefly
    so a burst of page loads still costs the hill a single request."""
    key = _SNAP_KEY.format(hill["id"])
    snap = cache.get(key)
    if snap is not None or not live_fallback:
        return snap or {}
    snap = _build_snapshot(hill, {}, time.time())
    cache.set(key, snap, timeout=min(settings.tick_seconds(), 10))
    return snap


# --------------------------------------------------------------------------
# Scorer
# --------------------------------------------------------------------------
def _score_once(app):
    with app.app_context():
        now = time.time()
        teams_mode = is_teams_mode()
        open_ = scoring_open()
        for hill in settings.hills():
            key = _SNAP_KEY.format(hill["id"])
            snap = _build_snapshot(hill, cache.get(key) or {}, now)
            cache.set(key, snap, timeout=_snapshot_ttl())
            if not open_ or not snap["online"]:
                continue
            # No fresh claim -> nobody scores this tick.
            if not snap["token"] or (now - snap["ts"]) > settings.fresh_window():
                continue
            if snap["holder_id"] is None:
                continue
            # Full points at root, half (rounded, floor 1) when the hold is only
            # user-level on a boot2root hill.
            value = hill["points"]
            if snap.get("level") == "user":
                value = max(1, hill["points"] // 2)
            award = Awards(
                name="{} — hill tick".format(hill["name"])[:_AWARD_NAME_MAX],
                category="koth:{}".format(hill["id"]),
                value=value,
                icon="crown",
            )
            if teams_mode:
                award.team_id = snap["holder_id"]
            else:
                award.user_id = snap["holder_id"]
            db.session.add(award)
        db.session.commit()
        cache.set("koth:last_tick", now, timeout=_snapshot_ttl())


def _scorer_loop(app):
    # Only one worker scores. Hold an exclusive fcntl lock for the process
    # lifetime; workers that fail to acquire it simply exit the loop.
    lock_file = open(_SCORER_LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return  # another worker owns the scorer
    while True:
        try:
            _score_once(app)
        except Exception:  # nosec B110 - scorer loop must survive a single bad pass
            pass
        time.sleep(settings.tick_seconds())


# --------------------------------------------------------------------------
# Player-facing state
# --------------------------------------------------------------------------
def _leaderboard(koth_id: str, name_by_id: dict, limit: int = 5, admin: bool = False):
    """Top holders of one hill. Honours the scoreboard freeze for non-admins,
    exactly like get_standings / Teams.get_awards."""
    col = Awards.team_id if is_teams_mode() else Awards.user_id
    q = db.session.query(col.label("aid"), db.func.sum(Awards.value).label("score"))
    q = q.filter(Awards.category == "koth:{}".format(koth_id))
    freeze = get_config("freeze")
    if freeze and not admin:
        q = q.filter(Awards.date < unix_time_to_utc(freeze))
    rows = q.group_by(col).order_by(db.func.sum(Awards.value).desc()).limit(limit).all()
    return [
        {"name": name_by_id.get(aid, "?"), "score": int(score or 0)}
        for aid, score in rows
        if aid is not None
    ]


def _hill_view(hill: dict, snap: dict, now: float, viewer_aid=None) -> dict:
    fresh = settings.fresh_window()
    token = snap.get("token") or ""
    ts = float(snap.get("ts") or 0)
    reign_since = snap.get("reign_since")
    return {
        "online": bool(snap.get("online")),
        "token_preview": (token[:8] + "…") if token else None,
        "holder": snap.get("holder_name"),
        "is_you": bool(viewer_aid is not None and snap.get("holder_id") == viewer_aid),
        "fresh": bool(token and (now - ts) <= fresh),
        "last_claim_seconds": int(max(0, now - ts)) if token else None,
        "reign_seconds": int(max(0, now - reign_since)) if reign_since else None,
        "takeovers": int(snap.get("takeovers") or 0),
        # "user" only on a boot2root hill held at user level (half points).
        "level": snap.get("level", "root"),
    }


@bp.route("/api/state")
@authed_only
@ratelimit(method="GET", limit=60, interval=60)
def api_state():
    user = get_current_user()
    aid = user.account_id
    admin = is_admin()
    now = time.time()
    name_by_id = dict(_accounts())
    out = []
    for hill in settings.hills():
        snap = get_snapshot(hill)
        out.append(
            {
                "id": hill["id"],
                "name": hill["name"],
                "player_url": hill["player_url"],
                "points": hill["points"],
                "your_token": koth_token_for(aid, hill["id"]),
                "king": _hill_view(hill, snap, now, viewer_aid=aid),
                "top": _leaderboard(hill["id"], name_by_id, admin=admin),
            }
        )
    return jsonify(
        {
            "active": settings.is_active(),
            "scoring": bool(settings.is_active() and scoring_open()),
            "frozen": bool(is_scoreboard_frozen() and not admin),
            "tick": settings.tick_seconds(),
            "fresh_window": settings.fresh_window(),
            "hills": out,
        }
    )


@bp.route("/api/holders")
@check_account_visibility
@check_score_visibility
@ratelimit(method="GET", limit=120, interval=60)
def api_holders():
    """Who holds each hill right now -- names only, for the scoreboard badge.
    Empty while the public scoreboard is frozen (revealing the holder would
    leak who is still scoring), unless the viewer is an admin."""
    if not settings.is_active() or (is_scoreboard_frozen() and not is_admin()):
        return jsonify({"success": True, "data": []})
    now = time.time()
    data = []
    for hill in settings.hills():
        snap = get_snapshot(hill)
        v = _hill_view(hill, snap, now)
        if snap.get("holder_id") is None or not v["fresh"]:
            continue
        data.append(
            {
                "hill_id": hill["id"],
                "hill": hill["name"],
                "account_id": snap["holder_id"],
                "name": snap.get("holder_name"),
                "reign_seconds": v["reign_seconds"],
            }
        )
    return jsonify({"success": True, "data": data})


@bp.route("/")
@authed_only
def page():
    return render_template("koth/index.html")


# --------------------------------------------------------------------------
# Admin: read-only status + calibration
# --------------------------------------------------------------------------
def _totals_by_hill():
    rows = (
        db.session.query(
            Awards.category, db.func.sum(Awards.value), db.func.count(Awards.id)
        )
        .filter(Awards.category.like("koth:%"))
        .group_by(Awards.category)
        .all()
    )
    return {c: {"points": int(p or 0), "ticks": int(n or 0)} for c, p, n in rows}


@bp.route("/api/admin")
@admins_only
def api_admin():
    now = time.time()
    tick = settings.tick_seconds()
    end = int(get_config("end") or 0)
    remaining = max(0, end - now) if end else None
    totals = _totals_by_hill()
    name_by_id = dict(_accounts())
    hills = []
    for hill in settings.hills():
        snap = get_snapshot(hill)
        v = _hill_view(hill, snap, now)
        t = totals.get("koth:{}".format(hill["id"]), {"points": 0, "ticks": 0})
        hills.append(
            {
                "id": hill["id"],
                "name": hill["name"],
                "url": hill["url"],
                "player_url": hill["player_url"],
                "points": hill["points"],
                "own_secret": hill["scorer_secret"] != settings.scorer_secret(),
                "king": v,
                "holder_token": (snap.get("token") or "")[:8] + "…"
                if snap.get("token")
                else None,
                "error": snap.get("error"),
                "polled_at": snap.get("polled_at"),
                "awarded_points": t["points"],
                "awarded_ticks": t["ticks"],
                "cap_remaining": int(hill["points"] * (remaining // tick))
                if remaining is not None
                else None,
                "top": _leaderboard(hill["id"], name_by_id, limit=10, admin=True),
            }
        )
    last_tick = cache.get("koth:last_tick")
    return jsonify(
        {
            "active": settings.is_active(),
            "scoring": bool(settings.is_active() and scoring_open()),
            "paused": ctf_paused(),
            "ctftime": ctftime(),
            "frozen": is_scoreboard_frozen(),
            "tick": tick,
            "fresh_window": settings.fresh_window(),
            "last_tick_seconds": int(now - last_tick) if last_tick else None,
            "remaining_seconds": int(remaining) if remaining is not None else None,
            "hills": hills,
        }
    )


@bp.route("/admin")
@admins_only
def admin_page():
    return render_template("koth/admin.html")


def load(app):
    app.register_blueprint(bp, url_prefix="/plugins/koth")
    register_user_page_menu_bar("King of the Hill", "/plugins/koth/")
    register_admin_plugin_menu_bar("King of the Hill", "/plugins/koth/admin")

    # The background scorer polls real hills; never run it under the test
    # harness (no hills, and it would race explicit _score_once calls).
    if settings.is_active() and not app.config.get("TESTING"):
        t = threading.Thread(target=_scorer_loop, args=(app,), daemon=True)
        t.start()
