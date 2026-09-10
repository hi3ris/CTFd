"""Per-team HMAC flag class.

Served challenges never ship their flag in a downloadable artifact. Each team's
instance derives its own flag from a per-team secret injected by the instancier:

    TEAM_SECRET = HMAC_SHA256(GLOBAL_SECRET, str(account_id)).hexdigest()
    flag        = "CTF{" + HMAC_SHA256(TEAM_SECRET, CHALLENGE_ID)[:24] + "}"

This flag class lets the scoreboard validate that flag without storing it: on
submission it recomputes the expected flag for the submitting team and compares
it in constant time. The challenge's `content` field holds CHALLENGE_ID (e.g.
"web-jwt-cousin"); GLOBAL_SECRET is read from the CTF_TEAM_FLAG_SECRET
environment variable, which MUST be the same value the instancier uses when it
computes TEAM_SECRET for each team's container. Keep that secret off the arena
and out of git.

In teams mode `account_id` is the team id, so a whole team shares one flag; in
users mode it is the user id. This matches how CTFd scopes solves and
prerequisites.
"""

import hashlib
import hmac
import os

from CTFd.plugins.flags import FLAG_CLASSES, BaseFlag, FlagException
from CTFd.plugins import register_plugin_assets_directory
from CTFd.utils.user import get_current_user


FLAG_PREFIX = "CTF{"
FLAG_SUFFIX = "}"
DIGEST_LEN = 24


def _global_secret() -> str:
    secret = os.environ.get("CTF_TEAM_FLAG_SECRET")
    if not secret:
        # Fail closed: without the secret we cannot derive any flag, so no
        # submission can be validated. Surfacing this is better than silently
        # rejecting every correct flag during the event.
        raise FlagException(
            "team_hmac flag misconfigured: CTF_TEAM_FLAG_SECRET is not set on CTFd."
        )
    return secret


def team_secret_for(account_id: int) -> str:
    """The per-team secret the instancier injects as TEAM_SECRET. Kept public so
    an out-of-band tool can reproduce it when provisioning a team's container."""
    return hmac.new(
        _global_secret().encode("utf-8"),
        str(account_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def challenge_secret_for(account_id: int, challenge_id: str) -> str:
    """The PER-CHALLENGE secret an instance receives (env CHALLENGE_SECRET).

    Derived from the team secret and the challenge id, so it is unique per team
    AND per challenge. Crucially it is NOT the team master secret: a player who
    fully owns one challenge's container (the goal of a pwn challenge) learns
    only this challenge's secret and cannot recompute any other challenge's
    flag for their team. The flag is the first 24 hex of this value."""
    return hmac.new(
        team_secret_for(account_id).encode("utf-8"),
        challenge_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def expected_flag(account_id: int, challenge_id: str) -> str:
    return FLAG_PREFIX + challenge_secret_for(account_id, challenge_id)[:DIGEST_LEN] + FLAG_SUFFIX


class CTFdTeamHmacFlag(BaseFlag):
    name = "team_hmac"
    # Reuse the static flag's admin widgets: authors just type CHALLENGE_ID in
    # the content field, exactly like a static flag.
    templates = {
        "create": "/plugins/flags/assets/static/create.html",
        "update": "/plugins/flags/assets/static/edit.html",
    }

    @staticmethod
    def compare(chal_key_obj, provided):
        challenge_id = (chal_key_obj.content or "").strip()
        if not challenge_id:
            raise FlagException(
                "team_hmac flag has no challenge id in its content field."
            )

        user = get_current_user()
        if user is None:
            # Submission always happens authenticated; if not, reject rather
            # than leak a flag computed against a null account.
            return False

        expected = expected_flag(user.account_id, challenge_id)

        # Constant-time comparison: never short-circuit on the first differing
        # byte, so submission timing cannot be used to recover the flag.
        return hmac.compare_digest(expected, provided.strip())


def load(app):
    FLAG_CLASSES["team_hmac"] = CTFdTeamHmacFlag
    register_plugin_assets_directory(
        app, base_path="/plugins/team_hmac_flag/assets/"
    )
