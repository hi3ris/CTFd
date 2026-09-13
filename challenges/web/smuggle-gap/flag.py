#!/usr/bin/env python3
"""Per-challenge dynamic flag derivation for challenge `web-smuggle-gap`.

The per-team instancier injects per-CHALLENGE values into each container, never
the team master secret:

    FLAG              the exact flag string, e.g. "NCTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "NCTF{" + CHALLENGE_SECRET[:24] + "}"

Historically the flag body was HMAC_SHA256(TEAM_SECRET, CHALLENGE_ID)[:24], and
the instancier sets CHALLENGE_SECRET == HMAC_SHA256(team_secret, CHALLENGE_ID),
so CHALLENGE_SECRET[:24] is exactly that same body -- the flag VALUE is
unchanged. TEAM_SECRET is NO LONGER injected at runtime; it is only consulted
as a LOCAL DEV fallback so the app still runs off-arena (local dev / playtest).

The flag is emitted ONLY by the running backend's internal route, and only when
that route is actually reached. It never ships in a downloadable artifact.

Usage (also runnable standalone for the platform's validation tooling):
    FLAG=NCTF{...} python3 flag.py            # echoes FLAG verbatim
    CHALLENGE_SECRET=<hex> python3 flag.py    # -> NCTF{<hex[:24]>}
    python3 flag.py                           # LOCAL DEV fallback
    python3 flag.py <team-secret>             # LOCAL DEV: derive from a secret
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "web-smuggle-gap"


def derive_flag(team_secret: str) -> str:
    """Legacy TEAM_SECRET-based derivation, kept for compatibility / local dev.

    Reproduces the historical value from a team secret. Only used off-arena; in
    production the flag comes from FLAG / CHALLENGE_SECRET (see get_flag).
    """
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "NCTF{" + digest[:24] + "}"


# Backwards-compatible alias for any caller expecting flag(secret).
flag = derive_flag


def get_flag() -> str:
    """Return this instance's flag under the per-challenge contract.

    Precedence:
      1. os.environ["FLAG"]                      -- exact flag injected by arena
      2. "NCTF{" + CHALLENGE_SECRET[:24] + "}"   -- per-challenge hex from arena
      3. LOCAL DEV fallback                       -- derived from TEAM_SECRET (or
         "local-dev-secret"). NEVER taken in production.
    """
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "NCTF{" + challenge_secret[:24] + "}"
    return derive_flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(derive_flag(sys.argv[1]))
    else:
        print(get_flag())
