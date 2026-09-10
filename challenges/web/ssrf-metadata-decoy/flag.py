#!/usr/bin/env python3
"""
Per-challenge dynamic flag (new per-challenge contract).

The per-team instancer injects per-challenge values into the container:

    FLAG              the exact flag string, e.g. "CTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "CTF{" + CHALLENGE_SECRET[:24] + "}"

The flag VALUE is unchanged from the previous per-team scheme

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "<challenge-id>")[:24] + "}"

because the instancer sets CHALLENGE_SECRET == HMAC_SHA256(team_secret,
CHALLENGE_ID), so CHALLENGE_SECRET[:24] is exactly the old flag body. This is a
SOURCE change, not a value change. TEAM_SECRET is no longer injected at runtime.

Usage:
    FLAG=... python3 flag.py                 # echoes FLAG verbatim
    CHALLENGE_SECRET=... python3 flag.py     # CTF{ CHALLENGE_SECRET[:24] }
    TEAM_SECRET=... python3 flag.py          # LOCAL DEV fallback only
    python3 flag.py <team_secret>            # LOCAL DEV fallback only
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "web-ssrf-metadata-decoy"

# Used ONLY for the local-dev fallback when neither FLAG nor CHALLENGE_SECRET is
# injected (i.e. running off-arena). Never used on a deployed team instance.
_DEV_TEAM_SECRET = "local-dev-secret"


def flag(secret: str) -> str:
    """Compatibility: derive the flag body from a raw team secret (local dev).

    Kept for backwards compatibility with older callers. Deployed instances go
    through get_flag() instead, which reads the injected per-challenge contract.
    """
    digest = hmac.new(
        secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256
    ).hexdigest()
    return "CTF{" + digest[:24] + "}"


# Legacy alias (the previous name of the compatibility helper).
compute = flag


def get_flag() -> str:
    """Return the flag under the per-challenge contract.

    In order:
      1. os.environ["FLAG"] if set (injected verbatim by the instancer).
      2. "CTF{" + os.environ["CHALLENGE_SECRET"][:24] + "}" if CHALLENGE_SECRET
         is set (per-challenge hex; body == old flag body).
      3. LOCAL DEV fallback: derived from os.environ.get("TEAM_SECRET",
         "local-dev-secret") so the challenge still runs off-arena.
    """
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "CTF{" + challenge_secret[:24] + "}"
    # LOCAL DEV fallback (off-arena only): derive from the dev team secret.
    return flag(os.environ.get("TEAM_SECRET", _DEV_TEAM_SECRET))


if __name__ == "__main__":
    # __main__ goes through get_flag() so the contract is honored. A raw team
    # secret may still be passed via argv for local dev when the arena env vars
    # are absent.
    if (
        len(sys.argv) > 1
        and not os.environ.get("FLAG")
        and not os.environ.get("CHALLENGE_SECRET")
    ):
        os.environ["TEAM_SECRET"] = sys.argv[1]
    print(get_flag())
