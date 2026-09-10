#!/usr/bin/env python3
"""
Per-challenge flag derivation for challenge `crypto-padding-oracle-lite`.

The platform instancier now injects PER-CHALLENGE values into the container,
not the team master secret:

    FLAG              the exact flag string, e.g. "CTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "CTF{" + CHALLENGE_SECRET[:24] + "}"

CHALLENGE_SECRET == HMAC_SHA256(team_secret, CHALLENGE_ID), so
CHALLENGE_SECRET[:24] is exactly the legacy flag body -- the flag VALUE is
unchanged, only the source contract is. TEAM_SECRET is no longer injected.

Resolution order used by get_flag():
    1. os.environ["FLAG"]                          if set
    2. "CTF{" + os.environ["CHALLENGE_SECRET"][:24] + "}"   if set
    3. LOCAL DEV fallback, derived from TEAM_SECRET (default "local-dev-secret")
       so the challenge still runs off-arena.

Usage:
    FLAG=CTF{...} python3 flag.py           # echoes FLAG
    CHALLENGE_SECRET=<hex> python3 flag.py  # echoes CTF{<hex[:24]>}
    python3 flag.py                         # LOCAL DEV fallback
    python3 flag.py <team-secret>           # legacy: derive from a team secret
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "crypto-padding-oracle-lite"

# LOCAL DEV ONLY -- used to derive a flag when neither FLAG nor CHALLENGE_SECRET
# is present in the environment (i.e. running off-arena). Never used on the arena.
_DEV_TEAM_SECRET_FALLBACK = "local-dev-secret"


def flag(team_secret: str) -> str:
    """Legacy per-team derivation, kept for compatibility / local dev only."""
    digest = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()
    return "CTF{" + digest[:24] + "}"


def get_flag() -> str:
    """Resolve the flag from the new per-challenge contract.

    Returns FLAG verbatim if present; otherwise derives it from CHALLENGE_SECRET;
    otherwise falls back to a clearly-marked LOCAL DEV value so the challenge
    still runs off-arena. No runtime dependence on TEAM_SECRET on the arena.
    """
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag

    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "CTF{" + challenge_secret[:24] + "}"

    # LOCAL DEV fallback (off-arena only).
    return flag(os.environ.get("TEAM_SECRET", _DEV_TEAM_SECRET_FALLBACK))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Legacy explicit team-secret path (local dev convenience).
        print(flag(sys.argv[1]))
    else:
        print(get_flag())
