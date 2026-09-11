#!/usr/bin/env python3
"""
Per-challenge flag derivation for challenge `ai-ai3-tool-abuse` (AI track, Level 3).

The flag VALUE is unchanged from the original design:

    flag = "NCTF{" + HMAC_SHA256(team_secret, "ai-ai3-tool-abuse")[:24] + "}"

but the container no longer receives the team MASTER secret. The per-team
instancer now injects only per-challenge values:

    FLAG              the exact flag string, e.g. "NCTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex, == HMAC_SHA256(team_secret, CHALLENGE_ID),
                      so CHALLENGE_SECRET[:24] is exactly the old flag body.

So `get_flag()` reads that contract (FLAG, then CHALLENGE_SECRET) and only falls
back to the old TEAM_SECRET math for LOCAL DEV runs off-arena. The scoreboard's
`team_hmac` flag class validates the same value it always did.

Usage:
    FLAG=NCTF{...} python3 flag.py                 # echoes FLAG
    CHALLENGE_SECRET=<hex> python3 flag.py        # NCTF{ CHALLENGE_SECRET[:24] }
    TEAM_SECRET=<team-secret> python3 flag.py     # LOCAL DEV fallback
    python3 flag.py <team-secret>                 # LOCAL DEV fallback
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "ai-ai3-tool-abuse"

# Clearly-marked LOCAL DEV secret, used only when neither FLAG nor
# CHALLENGE_SECRET is injected (i.e. running off-arena). Never used in the arena.
_DEV_TEAM_SECRET = "local-dev-secret"


def _hmac_hex(team_secret: str, label: str) -> str:
    return hmac.new(team_secret.encode(), label.encode(), hashlib.sha256).hexdigest()


def flag(team_secret: str) -> str:
    """Compatibility: reproduce the flag from a team master secret (dev/tooling)."""
    return "NCTF{" + _hmac_hex(team_secret, CHALLENGE_ID)[:24] + "}"


def _dev_challenge_secret() -> str:
    """LOCAL DEV: derive CHALLENGE_SECRET from the TEAM_SECRET dev fallback so
    off-arena runs still produce a stable, consistent flag."""
    team_secret = os.environ.get("TEAM_SECRET", _DEV_TEAM_SECRET)
    return _hmac_hex(team_secret, CHALLENGE_ID)


def get_flag() -> str:
    """Return the flag under the new per-challenge contract.

    Order:
      1. os.environ["FLAG"] if set (instancer injects the exact flag string);
      2. else "NCTF{" + os.environ["CHALLENGE_SECRET"][:24] + "}" if CHALLENGE_SECRET set;
      3. else a LOCAL DEV fallback derived from TEAM_SECRET (default
         "local-dev-secret") so the service still runs off-arena.
    """
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if not challenge_secret:
        # LOCAL DEV only: no per-challenge secret injected.
        challenge_secret = _dev_challenge_secret()
    return "NCTF{" + challenge_secret[:24] + "}"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Explicit team secret on argv -> dev/tooling compatibility path.
        print(flag(sys.argv[1]))
    else:
        print(get_flag())
