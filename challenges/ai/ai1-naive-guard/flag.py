#!/usr/bin/env python3
"""
Per-challenge flag derivation for challenge `ai-ai1-naive-guard`.

Runtime contract (per-challenge injection; TEAM_SECRET is NO LONGER injected):

    FLAG              the exact flag string, e.g. "CTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "CTF{" + CHALLENGE_SECRET[:24] + "}"

CHALLENGE_SECRET == HMAC_SHA256(team_secret, "ai-ai1-naive-guard"), so
CHALLENGE_SECRET[:24] is exactly the old flag body -- the flag VALUE is
unchanged, this is a SOURCE change only.

get_flag() returns, in order of preference:
    1. os.environ["FLAG"]                                   (arena: exact flag)
    2. "CTF{" + os.environ["CHALLENGE_SECRET"][:24] + "}"   (arena: per-challenge)
    3. a clearly-marked LOCAL DEV fallback derived from
       os.environ.get("TEAM_SECRET", "local-dev-secret")    (off-arena only)

The SIGMA secret the model guards is a DIFFERENT derivation, now keyed by
CHALLENGE_SECRET (label "guard-secret"); it is intentionally not the flag.
Pass --secret to print it too (useful for platform smoke tests).

Usage:
    python3 flag.py                         # echoes FLAG / per-challenge flag
    TEAM_SECRET=<team-secret> python3 flag.py   # local dev
    python3 flag.py <team-secret>               # local dev
    python3 flag.py <team-secret> --secret
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "ai-ai1-naive-guard"

# Local-dev fallback ONLY. On the arena, CHALLENGE_SECRET (and usually FLAG)
# is injected and TEAM_SECRET is never present, so this default is never used.
_DEV_TEAM_SECRET = "local-dev-secret"


def _hmac_hex(key: str, label: str) -> str:
    return hmac.new(key.encode(), label.encode(), hashlib.sha256).hexdigest()


def flag(team_secret: str) -> str:
    """Compatibility: reproduce the flag from a raw TEAM_SECRET (local dev /
    platform reproduction). Unchanged historical derivation."""
    return "CTF{" + _hmac_hex(team_secret, CHALLENGE_ID)[:24] + "}"


def get_challenge_secret() -> str:
    """The per-challenge hex. Prefers the injected CHALLENGE_SECRET; off-arena
    it is re-derived from the TEAM_SECRET dev fallback so local runs still work
    (and stay consistent with get_flag()/guard_secret())."""
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return cs
    team_secret = os.environ.get("TEAM_SECRET", _DEV_TEAM_SECRET)
    return _hmac_hex(team_secret, CHALLENGE_ID)


def get_flag() -> str:
    """The flag, following the runtime contract."""
    f = os.environ.get("FLAG")
    if f:
        return f
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return "CTF{" + cs[:24] + "}"
    # LOCAL DEV fallback (off-arena only).
    team_secret = os.environ.get("TEAM_SECRET", _DEV_TEAM_SECRET)
    return "CTF{" + _hmac_hex(team_secret, CHALLENGE_ID)[:24] + "}"


def guard_secret(challenge_secret: str = None) -> str:
    """The SIGMA secret the model is told to protect. Now derived from the
    per-challenge secret (label "guard-secret"), not TEAM_SECRET."""
    if challenge_secret is None:
        challenge_secret = get_challenge_secret()
    h = _hmac_hex(challenge_secret, "guard-secret")[:16].upper()
    return f"SIGMA-{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--secret"]
    show_secret = "--secret" in sys.argv[1:]
    # A raw TEAM_SECRET may be passed as argv[1] for local dev / reproduction;
    # surface it via the env the contract reads so get_flag() stays the single
    # source of truth.
    if args:
        os.environ["TEAM_SECRET"] = args[0]
    print(get_flag())
    if show_secret:
        print(guard_secret())
