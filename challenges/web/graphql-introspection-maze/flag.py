#!/usr/bin/env python3
"""
Per-challenge flag derivation for challenge `web-graphql-introspection-maze`.

The per-team instancer now injects PER-CHALLENGE values into the container:

    FLAG              the exact flag string, e.g. "CTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "CTF{" + CHALLENGE_SECRET[:24] + "}"

TEAM_SECRET is NO LONGER injected. The flag VALUE is unchanged: previously

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "web-graphql-introspection-maze")[:24] + "}"

and CHALLENGE_SECRET == HMAC(team_secret, CHALLENGE_ID), so CHALLENGE_SECRET[:24]
is exactly the old flag body. This is a SOURCE change, not a value change.

The flag is emitted by the running instance only after the privileged effect
(session clearance -> ROOT) has actually occurred.

Usage:
    python3 flag.py            # echoes FLAG / derives from CHALLENGE_SECRET
    TEAM_SECRET=<s> python3 flag.py   # LOCAL DEV only, reproduces old value
    python3 flag.py <team-secret>     # LOCAL DEV compatibility helper
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "web-graphql-introspection-maze"


def flag(team_secret: str) -> str:
    """Legacy per-team derivation. Kept for compatibility / local dev only."""
    digest = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()
    return "CTF{" + digest[:24] + "}"


def get_flag() -> str:
    """Resolve the flag under the new per-challenge contract.

    Order:
      1. os.environ["FLAG"] if set (injected by the platform);
      2. else "CTF{" + os.environ["CHALLENGE_SECRET"][:24] + "}" if set;
      3. else a clearly-marked LOCAL DEV fallback derived from the
         TEAM_SECRET dev value, so this still runs off-arena.
    """
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "CTF{" + challenge_secret[:24] + "}"
    # LOCAL DEV fallback ONLY -- never reached on the arena, where FLAG /
    # CHALLENGE_SECRET are always injected.
    return flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    # A positional team-secret arg is a local-dev convenience; otherwise go
    # through get_flag() so `export FLAG=$(python3 flag.py)` echoes FLAG.
    if len(sys.argv) > 1:
        print(flag(sys.argv[1]))
    else:
        print(get_flag())
