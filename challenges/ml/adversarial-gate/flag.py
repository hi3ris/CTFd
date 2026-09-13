#!/usr/bin/env python3
"""
Per-challenge flag derivation for challenge `ml-adversarial-gate`.

The per-team instancer now injects PER-CHALLENGE values into the served
container (it no longer injects the team MASTER secret TEAM_SECRET, so owning
one container no longer leaks every flag for the team):

    FLAG              the exact flag string, e.g. "NCTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24]
                      i.e. FLAG == "NCTF{" + CHALLENGE_SECRET[:24] + "}"

The flag VALUE is unchanged: previously the flag was
    flag = "NCTF{" + HMAC_SHA256(TEAM_SECRET, CHALLENGE_ID)[:24] + "}"
and the instancer computes CHALLENGE_SECRET = HMAC(team_secret, CHALLENGE_ID),
so CHALLENGE_SECRET[:24] is exactly the old flag body. The scoreboard's
team_hmac flag class validates the same value. This is a SOURCE change, not a
value change.

Usage (arena):    the container already has FLAG / CHALLENGE_SECRET in env
Usage (local dev): TEAM_SECRET=<team-secret> python3 flag.py
                   python3 flag.py <team-secret>
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "ml-adversarial-gate"


def flag(team_secret: str) -> str:
    """Legacy derivation kept for compatibility / local dev.

    HMAC(team_secret, CHALLENGE_ID)[:24] is exactly CHALLENGE_SECRET[:24], so
    this reproduces the same flag body off-arena where only a team secret is
    available.
    """
    dig = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()
    return "NCTF{" + dig[:24] + "}"


def get_flag() -> str:
    """Return the flag under the new per-challenge contract.

    Order:
      1. os.environ["FLAG"]                    -- exact flag, if injected
      2. "NCTF{" + CHALLENGE_SECRET[:24] + "}"  -- if CHALLENGE_SECRET injected
      3. LOCAL DEV fallback derived from TEAM_SECRET (default "local-dev-secret")
         so the service still runs off-arena.
    """
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return "NCTF{" + cs[:24] + "}"
    # LOCAL DEV fallback only -- never used in the arena.
    return flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    # Explicit team secret on argv reproduces the flag off-arena; otherwise go
    # through the full get_flag() contract (FLAG / CHALLENGE_SECRET / dev).
    if len(sys.argv) > 1:
        print(flag(sys.argv[1]))
    else:
        print(get_flag())
