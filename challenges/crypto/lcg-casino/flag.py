#!/usr/bin/env python3
"""
Per-challenge flag resolution for challenge `crypto-lcg-casino`.

The platform instancier injects PER-CHALLENGE values into the container:

    FLAG              the exact flag string, e.g. "NCTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "NCTF{" + CHALLENGE_SECRET[:24] + "}"

TEAM_SECRET is NO LONGER injected. The flag VALUE is unchanged: historically
    flag = "NCTF{" + HMAC_SHA256(TEAM_SECRET, "crypto-lcg-casino")[:24] + "}"
and CHALLENGE_SECRET == HMAC_SHA256(team_secret, "crypto-lcg-casino"), so
CHALLENGE_SECRET[:24] is exactly the old flag body. This is a SOURCE change,
not a value change.

get_flag() resolves, in order:
    1. os.environ["FLAG"] if set (arena: instancier injects the exact string);
    2. else "NCTF{" + os.environ["CHALLENGE_SECRET"][:24] + "}" if set (arena);
    3. else a clearly-marked LOCAL DEV fallback derived from
       os.environ.get("TEAM_SECRET", "local-dev-secret"), so this still runs
       off-arena during local build + smoke tests.

Usage:
    FLAG=NCTF{...} python3 flag.py           # echoes FLAG
    CHALLENGE_SECRET=<hex> python3 flag.py   # echoes NCTF{<hex[:24]>}
    python3 flag.py                          # LOCAL DEV fallback
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "crypto-lcg-casino"


def flag(secret: str) -> str:
    """Legacy per-team derivation, kept for compatibility.

    Equivalent to "NCTF{" + HMAC_SHA256(secret, CHALLENGE_ID)[:24] + "}".
    In the new contract this is used only to reproduce the LOCAL DEV flag from
    a dev TEAM_SECRET; on the arena the flag comes from FLAG / CHALLENGE_SECRET.
    """
    digest = hmac.new(secret.encode(), CHALLENGE_ID.encode(),
                      hashlib.sha256).hexdigest()
    return "NCTF{" + digest[:24] + "}"


def get_flag() -> str:
    """Resolve the flag for the running service under the per-challenge contract."""
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag

    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "NCTF{" + challenge_secret[:24] + "}"

    # LOCAL DEV fallback ONLY -- never hit on the arena, where FLAG /
    # CHALLENGE_SECRET are always injected. Derives the same value the old
    # TEAM_SECRET path would have produced, so local runs still work.
    dev_team_secret = os.environ.get("TEAM_SECRET", "local-dev-secret")
    return flag(dev_team_secret)


if __name__ == "__main__":
    print(get_flag())
