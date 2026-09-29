"""Team minimum size — an NCTF26 rule CTFd does not have natively.

CTFd only knows a *maximum* team size (``team_size``). NCTF26 wants teams of
4 to 5 players: the maximum is the stock setting, this plugin adds the minimum
(``team_size_min`` config, integer, 0 or empty = disabled).

An incomplete team can still register, join and browse challenges; what it
cannot do until it reaches the minimum is *play*:

  * ``POST /api/v1/challenges/attempt`` (flag submission) -> 403 with the usual
    ``{"status": "incorrect", "message": ...}`` shape, so the theme shows the
    explanation in the answer box instead of a raw error;
  * ``POST /plugins/team_instancer/spawn`` (per-team instance) -> 403 JSON.

Admins are never blocked (they have no team). Users mode: nothing to enforce.
The gate is an app-scoped ``before_request`` (same pattern as token_lockdown):
it runs after CTFd populated the current user, and leaves no global state.

Admin: *Admin -> Config* has no field for it; set it through the API:
``PATCH /api/v1/configs {"team_size_min": 4}`` (see deploy/PROD-SETUP.md).
"""

from flask import jsonify, request

from CTFd.utils import get_config
from CTFd.utils.config import is_teams_mode
from CTFd.utils.user import get_current_team, get_current_user, is_admin

_ATTEMPT_PATH = "/api/v1/challenges/attempt"
_SPAWN_PATH = "/plugins/team_instancer/spawn"


def team_size_min():
    try:
        return int(get_config("team_size_min") or 0)
    except (TypeError, ValueError):
        return 0


def _blocked_reason():
    """Message if the current team is below the minimum, else None."""
    minimum = team_size_min()
    if minimum <= 0 or not is_teams_mode() or is_admin():
        return None
    user = get_current_user()
    if user is None or user.team_id is None:
        return None  # CTFd / the instancer already refuse team-less users
    team = get_current_team()
    if team is None:
        return None
    members = len(team.members)
    if members >= minimum:
        return None
    return (
        "Equipe incomplete : %d membre%s sur %d minimum. Recrutez avant de jouer."
        % (members, "s" if members > 1 else "", minimum)
    )


def load(app):
    @app.before_request
    def _gate_incomplete_teams():
        if request.method != "POST":
            return
        path = request.path.rstrip("/")
        if path == _ATTEMPT_PATH:
            reason = _blocked_reason()
            if reason:
                return (
                    jsonify(
                        {
                            "success": True,
                            "data": {"status": "incorrect", "message": reason},
                        }
                    ),
                    403,
                )
        elif path == _SPAWN_PATH:
            reason = _blocked_reason()
            if reason:
                return jsonify({"success": False, "error": reason}), 403
