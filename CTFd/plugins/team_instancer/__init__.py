"""Per-team Docker instancer for CTFd.

A challenge type `team_instance` (dynamic scoring + a docker image) plus the
machinery to give each team its own container, exposed through FRP, with the
flag validated by the separate team_hmac_flag plugin. The instancer never
generates or stores a flag: it injects TEAM_SECRET and lets the container
derive it, exactly as team_hmac_flag recomputes it on submission.

Inactive when DOCKER_HOST is empty (out of event): the challenge type still
loads and challenges stay visible, but spawn returns 503.
"""

import datetime
import fcntl
import threading
import time

from flask import Blueprint, request

from CTFd.models import Challenges, Flags, Solves, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.plugins.dynamic_challenges.decay import DECAY_FUNCTIONS, logarithmic
from CTFd.plugins.migrations import upgrade
from CTFd.utils.decorators import authed_only, during_ctf_time_only, ratelimit
from CTFd.utils.decorators.visibility import check_challenge_visibility
from CTFd.utils.user import get_current_user
from CTFd.utils.config import is_teams_mode

from . import backend, frp, settings
from .models import TeamInstance, TeamInstanceChallenge


# --------------------------------------------------------------------------
# Challenge type
# --------------------------------------------------------------------------

class TeamInstanceValueChallenge(BaseChallenge):
    id = "team_instance"
    name = "team_instance"
    templates = {
        "create": "/plugins/team_instancer/assets/create.html",
        "update": "/plugins/team_instancer/assets/update.html",
        "view": "/plugins/team_instancer/assets/view.html",
    }
    scripts = {
        "create": "/plugins/team_instancer/assets/create.js",
        "update": "/plugins/team_instancer/assets/update.js",
        "view": "/plugins/team_instancer/assets/view.js",
    }
    route = "/plugins/team_instancer/assets/"
    blueprint = Blueprint(
        "team_instancer", __name__, template_folder="templates", static_folder="assets"
    )
    challenge_model = TeamInstanceChallenge

    @classmethod
    def calculate_value(cls, challenge):
        f = DECAY_FUNCTIONS.get(challenge.function, logarithmic)
        challenge.value = f(challenge)
        db.session.commit()
        return challenge

    @classmethod
    def read(cls, challenge):
        challenge = TeamInstanceChallenge.query.filter_by(id=challenge.id).first()
        data = super().read(challenge)
        data.update(
            {
                "initial": challenge.initial,
                "decay": challenge.decay,
                "minimum": challenge.minimum,
                "function": challenge.function,
                "docker_image": challenge.docker_image,
                "internal_port": challenge.internal_port,
            }
        )
        return data

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json()
        for attr, value in data.items():
            if attr in ("initial", "minimum", "decay"):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    value = 0
            setattr(challenge, attr, value)
        return TeamInstanceValueChallenge.calculate_value(challenge)

    @classmethod
    def solve(cls, user, team, challenge, request):
        super().solve(user, team, challenge, request)
        TeamInstanceValueChallenge.calculate_value(challenge)


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------

def _account_id():
    """The scoring/solve account: the team in teams mode, else the user."""
    user = get_current_user()
    if user is None:
        return None
    return user.account_id


def _prereqs_met(user, challenge):
    """Replays CTFd's own prerequisite gate (challenges.py) so a player cannot
    reach a locked challenge's instance by hitting this API directly."""
    if challenge.state == "hidden":
        return "hidden"
    if challenge.state == "locked":
        return "locked"
    if challenge.requirements:
        requirements = challenge.requirements.get("prerequisites", [])
        solve_ids = {
            cid for cid, in Solves.query.with_entities(Solves.challenge_id)
            .filter_by(account_id=user.account_id).all()
        }
        all_ids = {c.id for c in Challenges.query.with_entities(Challenges.id).all()}
        prereqs = set(requirements).intersection(all_ids)
        if not solve_ids >= prereqs:
            return "locked"
    return None


def _connection_info(port):
    host = settings.FRONT_PUBLIC_IP or "<front-ip>"
    return {"host": host, "port": port}


def _remaining_seconds(instance):
    if instance.start_time is None:
        return 0
    elapsed = (datetime.datetime.utcnow() - instance.start_time).total_seconds()
    return max(0, int(settings.INSTANCE_TTL - elapsed))


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

bp = TeamInstanceValueChallenge.blueprint


def _json(payload, code=200):
    from flask import jsonify
    return jsonify(payload), code


@bp.route("/spawn", methods=["POST"])
@check_challenge_visibility
@authed_only
@during_ctf_time_only
@ratelimit(method="POST", limit=6, interval=60)
def spawn():
    if not settings.is_active():
        return _json({"success": False, "error": "Instancier inactif hors evenement."}, 503)

    user = get_current_user()
    if is_teams_mode() and user.team_id is None:
        return _json({"success": False, "error": "Rejoignez une equipe d'abord."}, 403)

    data = request.get_json(silent=True) or request.form
    challenge_id = data.get("challenge_id")
    challenge = TeamInstanceChallenge.query.filter_by(id=challenge_id).first()
    if challenge is None:
        return _json({"success": False, "error": "Challenge introuvable."}, 404)

    gate = _prereqs_met(user, challenge)
    if gate == "hidden":
        return _json({"success": False, "error": "Introuvable."}, 404)
    if gate == "locked":
        return _json({"success": False, "error": "Prerequis non remplis."}, 403)

    account_id = user.account_id

    # Cap: one instance per (team, challenge) — also enforced by the DB unique
    # constraint, checked here for a clean message.
    existing = TeamInstance.query.filter_by(
        account_id=account_id, challenge_id=challenge.id
    ).first()
    if existing:
        return _json({
            "success": True, "status": existing.status,
            "connection": _connection_info(existing.port),
            "remaining": _remaining_seconds(existing),
        })

    # Cap: concurrent instances per team, and global.
    if TeamInstance.query.filter_by(account_id=account_id).count() >= settings.MAX_PER_TEAM:
        return _json({"success": False, "error": f"Maximum {settings.MAX_PER_TEAM} instances simultanees par equipe."}, 429)
    if TeamInstance.query.count() >= settings.MAX_TOTAL:
        return _json({"success": False, "error": "Capacite maximale atteinte, reessayez bientot."}, 503)

    # The challenge id label lives in the team_hmac flag's content. We inject
    # only the per-challenge secret and the concrete flag — never the team
    # master secret, so a compromised container cannot yield other flags.
    from CTFd.plugins.team_hmac_flag import challenge_secret_for, expected_flag
    flag_row = Flags.query.filter_by(challenge_id=challenge.id, type="team_hmac").first()
    if flag_row is None or not (flag_row.content or "").strip():
        return _json({"success": False, "error": "Challenge mal configure (flag team_hmac absent)."}, 500)
    label = flag_row.content.strip()
    container_env = {
        "FLAG": expected_flag(account_id, label),
        "CHALLENGE_SECRET": challenge_secret_for(account_id, label),
    }

    instance = TeamInstance(
        account_id=account_id, challenge_id=challenge.id, status="spawning",
        proxy_name=frp.proxy_name(account_id, challenge.id),
    )
    db.session.add(instance)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return _json({"success": False, "error": "Instance deja en cours de creation."}, 409)

    port = frp.allocate_port(instance.id, account_id, challenge.id)
    if port is None:
        db.session.delete(instance)
        db.session.commit()
        return _json({"success": False, "error": "Aucun port disponible, reessayez bientot."}, 503)
    instance.port = port

    try:
        cid, net = backend.spawn_container(account_id, challenge, container_env, port)
        instance.container_id = cid
        instance.network_name = net
        backend.add_frp_for(instance)
        instance.status = "running"
        db.session.commit()
    except Exception as e:
        instance.status = "error"
        db.session.commit()
        backend.teardown(instance)
        db.session.delete(instance)
        db.session.commit()
        return _json({"success": False, "error": f"Echec du demarrage: {e}"}, 500)

    return _json({
        "success": True, "status": "running",
        "connection": _connection_info(port),
        "remaining": _remaining_seconds(instance),
    })


@bp.route("/status", methods=["GET"])
@authed_only
def status():
    account_id = _account_id()
    challenge_id = request.args.get("challenge_id")
    instance = TeamInstance.query.filter_by(
        account_id=account_id, challenge_id=challenge_id
    ).first()
    if instance is None:
        return _json({"success": True, "status": "none"})
    return _json({
        "success": True, "status": instance.status,
        "connection": _connection_info(instance.port),
        "remaining": _remaining_seconds(instance),
    })


@bp.route("/renew", methods=["POST"])
@authed_only
@during_ctf_time_only
def renew():
    account_id = _account_id()
    data = request.get_json(silent=True) or request.form
    instance = TeamInstance.query.filter_by(
        account_id=account_id, challenge_id=data.get("challenge_id")
    ).first()
    if instance is None:
        return _json({"success": False, "error": "Aucune instance."}, 404)
    if instance.renew_count >= settings.MAX_RENEW_COUNT:
        return _json({"success": False, "error": "Nombre maximal de prolongations atteint."}, 429)
    instance.start_time = datetime.datetime.utcnow()
    instance.renew_count += 1
    db.session.commit()
    return _json({"success": True, "remaining": _remaining_seconds(instance)})


@bp.route("/destroy", methods=["POST"])
@authed_only
def destroy():
    account_id = _account_id()
    data = request.get_json(silent=True) or request.form
    instance = TeamInstance.query.filter_by(
        account_id=account_id, challenge_id=data.get("challenge_id")
    ).first()
    if instance is None:
        return _json({"success": True, "status": "none"})
    backend.teardown(instance)
    db.session.delete(instance)
    db.session.commit()
    return _json({"success": True, "status": "destroyed"})


# --------------------------------------------------------------------------
# Reaper: single-worker background thread, fcntl-locked.
# --------------------------------------------------------------------------

_REAPER_LOCK_PATH = "/tmp/ctfd_team_instancer.lock"


def _reap_once(app):
    with app.app_context():
        now = datetime.datetime.utcnow()
        cutoff = now - datetime.timedelta(seconds=settings.INSTANCE_TTL)
        expired = TeamInstance.query.filter(TeamInstance.start_time < cutoff).all()
        for inst in expired:
            backend.teardown(inst)
            db.session.delete(inst)
        db.session.commit()

        # Reconciliation: drop DB rows whose container has vanished, and (best
        # effort) leave arena-side orphans to be cleaned by the next arena
        # rebuild, which purges the whole table (see reconcile_on_boot).
        if settings.is_active() and backend.docker is not None:
            try:
                live = backend.list_live_container_ids()
                for inst in TeamInstance.query.all():
                    if inst.container_id and inst.container_id not in live:
                        # Full teardown, not just release_port: otherwise the
                        # dead instance's frp proxy stanza survives and, when
                        # its port is reallocated, two proxies claim it.
                        backend.teardown(inst)
                        db.session.delete(inst)
                db.session.commit()
            except Exception:
                db.session.rollback()


def _reaper_loop(app):
    # Only one worker should reap. Hold an exclusive fcntl lock for the process
    # lifetime; workers that fail to acquire it simply exit the loop.
    lock_file = open(_REAPER_LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return  # another worker owns the reaper
    while True:
        try:
            _reap_once(app)
        except Exception:
            pass
        time.sleep(settings.REAP_INTERVAL)


# --------------------------------------------------------------------------
# Plugin entry point
# --------------------------------------------------------------------------

def load(app):
    upgrade(plugin_name="team_instancer")
    CHALLENGE_CLASSES["team_instance"] = TeamInstanceValueChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/team_instancer/assets/"
    )
    app.register_blueprint(bp, url_prefix="/plugins/team_instancer")

    # Seed the port pool (no-op if already populated or table missing).
    try:
        frp.ensure_port_pool()
    except Exception:
        pass

    # Start the reaper only when the instancer is active.
    if settings.is_active():
        t = threading.Thread(target=_reaper_loop, args=(app,), daemon=True)
        t.start()
