#!/usr/bin/env python3
"""
Per-challenge flag derivation for challenge `web-jwt-cousin`.

The per-team instancier now injects per-CHALLENGE values into the container,
never the team master secret:

    FLAG              the exact flag string, e.g. "NCTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "NCTF{" + CHALLENGE_SECRET[:24] + "}"

Historically the flag was:

    flag = "NCTF{" + HMAC_SHA256(TEAM_SECRET, "web-jwt-cousin")[:24] + "}"

and the instancier sets CHALLENGE_SECRET == HMAC_SHA256(team_secret,
"web-jwt-cousin"), so CHALLENGE_SECRET[:24] is exactly the old flag body and
the flag VALUE is unchanged. TEAM_SECRET is NO LONGER injected at runtime.

Usage:
    FLAG=NCTF{...} python3 flag.py            # echoes FLAG verbatim
    CHALLENGE_SECRET=<hex> python3 flag.py   # -> NCTF{<hex[:24]>}
    python3 flag.py                          # LOCAL DEV fallback (see below)
    python3 flag.py <team-secret>            # LOCAL DEV: derive from a secret
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "web-jwt-cousin"


def flag(team_secret: str) -> str:
    """Legacy derivation kept for compatibility / local dev.

    Reproduces the historical value from a team secret. Only used off-arena:
    in production the flag comes from FLAG / CHALLENGE_SECRET (see get_flag).
    """
    digest = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()
    return "NCTF{" + digest[:24] + "}"


def get_flag() -> str:
    """Return this instance's flag under the per-challenge contract.

    Precedence:
      1. os.environ["FLAG"]                  -- exact flag injected by arena
      2. "NCTF{" + CHALLENGE_SECRET[:24] + "}" -- per-challenge hex from arena
      3. LOCAL DEV fallback                   -- derived from TEAM_SECRET (or
         "local-dev-secret") so the challenge still runs off-arena. This path
         is NEVER taken in production, where FLAG/CHALLENGE_SECRET are set.
    """
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "NCTF{" + challenge_secret[:24] + "}"
    # LOCAL DEV ONLY -- no per-challenge secret present.
    return flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # LOCAL DEV convenience: derive from an explicit team secret.
        print(flag(sys.argv[1]))
    else:
        print(get_flag())
