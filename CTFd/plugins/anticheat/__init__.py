"""Flag-sharing detector for per-team (`team_hmac`) flags.

Every `team_hmac` flag is derived per account (see plugins/team_hmac_flag):
team A's flag for a challenge is worthless to team B *unless B submits it*. When
that happens CTFd only records a plain wrong submission (`Fails.provided`) --
yet that value is, byte for byte, A's valid flag. It is the cleanest evidence of
flag sharing a CTF can produce, and it is already in the database.

This plugin turns it into a list of **incidents**: for each wrong submission on a
challenge that carries a `team_hmac` flag, recompute the expected flag of every
account and see whether `provided` is somebody *else's* flag. An incident names
the submitter, the flag's owner, the challenge, the IP and the time.

Design choices (deliberate):

  * No new table, no migration. Incidents are re-derived from `Fails` and the
    flag secret, cached under one key with a `Fails.id` cursor so that only new
    submissions are examined on each poll. `?rebuild=1` throws the cache away
    (needed after rotating CTF_TEAM_FLAG_SECRET or adding a team_hmac flag to a
    challenge that already has fails).
  * No `Notifications`: CTFd notifications are global (every player sees them),
    so an admin alert would leak the incident to the whole room. Instead each new
    incident is written to the `submissions` log (logs/submissions.log) and the
    admin page polls the API.
  * It signals, it never sanctions. Banning stays a human decision (règlement).
  * Hidden/banned accounts are part of the owner index (a "retired" team's flag
    circulating is still sharing) and flagged as such in the incident.
"""

import csv
import io
import logging

from flask import Blueprint, Response, jsonify, render_template, request

from CTFd.cache import cache
from CTFd.models import Challenges, Fails, Flags
from CTFd.plugins import register_admin_plugin_menu_bar
from CTFd.plugins.team_hmac_flag import expected_flag
from CTFd.utils.config import is_teams_mode
from CTFd.utils.decorators import admins_only
from CTFd.utils.modes import get_model

bp = Blueprint("anticheat", __name__, template_folder="templates")

CACHE_KEY = "anticheat:incidents"
CACHE_TTL = 6 * 3600  # a rebuild is cheap; this only bounds staleness
_journal = logging.getLogger("submissions")

# Spreadsheet formula injection: a cell starting with one of these would be
# evaluated by Excel/LibreOffice when the CSV is opened.
_CSV_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


# --------------------------------------------------------------------------
# Indexes
# --------------------------------------------------------------------------
def hmac_slugs():
    """{challenge_id: [slug, ...]} for every challenge carrying a team_hmac flag."""
    out = {}
    for f in Flags.query.filter_by(type="team_hmac").all():
        slug = (f.content or "").strip()
        if slug:
            out.setdefault(f.challenge_id, []).append(slug)
    return out


def accounts():
    """All scoring accounts (teams in teams mode, users otherwise), including
    hidden and banned ones: their flags can still circulate."""
    model = get_model()
    return [
        {"id": a.id, "name": a.name, "hidden": bool(a.hidden), "banned": bool(a.banned)}
        for a in model.query.with_entities(
            model.id, model.name, model.hidden, model.banned
        ).all()
    ]


def owner_index(slug, accts):
    """{expected flag: account id} for one challenge slug across every account.

    A dict lookup is not constant-time, but nothing here is exposed to players:
    this runs offline, admin-only, over submissions that were already rejected.
    """
    return {expected_flag(a["id"], slug): a["id"] for a in accts}


# --------------------------------------------------------------------------
# Scan
# --------------------------------------------------------------------------
def _account_of(fail):
    return fail.team_id if is_teams_mode() else fail.user_id


def scan(since_id=0):
    """Examine every wrong submission with id > since_id. Returns
    (incidents, last_fail_id_seen)."""
    slugs = hmac_slugs()
    if not slugs:
        last = Fails.query.with_entities(Fails.id).order_by(Fails.id.desc()).first()
        return [], (last[0] if last else since_id)

    accts = accounts()
    by_id = {a["id"]: a for a in accts}
    chal_names = dict(
        Challenges.query.with_entities(Challenges.id, Challenges.name)
        .filter(Challenges.id.in_(list(slugs)))
        .all()
    )
    indexes = {}  # slug -> owner index, built lazily

    incidents = []
    cursor = since_id
    q = Fails.query.filter(Fails.id > since_id).order_by(Fails.id.asc())
    for fail in q.all():
        cursor = fail.id
        chal_slugs = slugs.get(fail.challenge_id)
        if not chal_slugs:
            continue
        provided = (fail.provided or "").strip()
        submitter = _account_of(fail)
        for slug in chal_slugs:
            idx = indexes.get(slug)
            if idx is None:
                idx = indexes[slug] = owner_index(slug, accts)
            owner = idx.get(provided)
            if owner is None or owner == submitter:
                continue
            o = by_id.get(owner, {})
            s = by_id.get(submitter, {})
            incidents.append(
                {
                    "id": fail.id,
                    "date": fail.date.isoformat() if fail.date else None,
                    "challenge_id": fail.challenge_id,
                    "challenge": chal_names.get(fail.challenge_id, "?"),
                    "submitter_id": submitter,
                    "submitter": s.get("name", "?"),
                    "submitter_hidden": bool(s.get("hidden")),
                    "submitter_banned": bool(s.get("banned")),
                    "owner_id": owner,
                    "owner": o.get("name", "?"),
                    "owner_hidden": bool(o.get("hidden")),
                    "owner_banned": bool(o.get("banned")),
                    "ip": fail.ip,
                }
            )
            break  # one incident per submission
    return incidents, cursor


def incidents(rebuild=False):
    """Cached, incremental list of incidents (oldest first)."""
    state = None if rebuild else cache.get(CACHE_KEY)
    if not isinstance(state, dict):
        state = {"cursor": 0, "incidents": []}
    new, cursor = scan(since_id=state["cursor"])
    for inc in new:
        _journal.warning(
            "ANTICHEAT shared flag: %s (#%s) submitted the flag of %s (#%s) on "
            "challenge %r (#%s) from %s at %s [fail #%s]",
            inc["submitter"],
            inc["submitter_id"],
            inc["owner"],
            inc["owner_id"],
            inc["challenge"],
            inc["challenge_id"],
            inc["ip"],
            inc["date"],
            inc["id"],
        )
    if new or cursor != state["cursor"] or rebuild:
        state = {"cursor": cursor, "incidents": state["incidents"] + new}
        cache.set(CACHE_KEY, state, timeout=CACHE_TTL)
    return state


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _csv_cell(v):
    s = "" if v is None else str(v)
    return "'" + s if s.startswith(_CSV_DANGEROUS) else s


_CSV_COLUMNS = (
    "date",
    "fail_id",
    "submitter",
    "submitter_id",
    "owner",
    "owner_id",
    "challenge",
    "challenge_id",
    "ip",
)


def _to_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(_CSV_COLUMNS)
    for r in rows:
        w.writerow(_csv_cell(r[k] if k != "fail_id" else r["id"]) for k in _CSV_COLUMNS)
    return buf.getvalue()


@bp.route("/api/incidents")
@admins_only
def api_incidents():
    rebuild = request.args.get("rebuild") in ("1", "true", "yes")
    try:
        since = int(request.args.get("since_id", 0))
    except ValueError:
        since = 0
    state = incidents(rebuild=rebuild)
    rows = [i for i in state["incidents"] if i["id"] > since]
    if request.args.get("format") == "csv":
        return Response(
            _to_csv(rows),
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=anticheat-incidents.csv"
            },
        )
    return jsonify(
        {
            "success": True,
            "data": {
                "mode": "teams" if is_teams_mode() else "users",
                "cursor": state["cursor"],
                "hmac_challenges": len(hmac_slugs()),
                "accounts": get_model().query.count(),
                "total": len(state["incidents"]),
                "count": len(rows),
                "incidents": rows,
            },
        }
    )


@bp.route("/admin")
@admins_only
def admin_page():
    return render_template("anticheat/admin.html")


def load(app):
    app.register_blueprint(bp, url_prefix="/plugins/anticheat")
    register_admin_plugin_menu_bar("Anti-triche", "/plugins/anticheat/admin")
