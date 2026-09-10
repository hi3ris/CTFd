#!/usr/bin/env python3
"""
Per-challenge flag / secret derivation for challenge `ai-ai2-output-filter`.

NEW CONTRACT (per-challenge injection, not the team master secret):

    FLAG              the exact flag string, e.g. "CTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "CTF{" + CHALLENGE_SECRET[:24] + "}"

The platform injects FLAG and CHALLENGE_SECRET into the container at creation
time; TEAM_SECRET is NO LONGER injected. Because
CHALLENGE_SECRET == HMAC_SHA256(team_secret, "ai-ai2-output-filter"), taking
CHALLENGE_SECRET[:24] reproduces exactly the old flag body, so the flag VALUE
is unchanged -- this is a SOURCE change only.

The SIGMA value the model guards is a DIFFERENT (auxiliary) per-challenge
derivation. It now derives from CHALLENGE_SECRET (label "guarded"); it is
intentionally NOT the flag -- a player recovers it past the output filter and
submits it to /verify, which returns the flag above. Pass --secret to print the
guarded value too (useful for platform smoke tests). These derivations match
app.py exactly.

Usage:
    python3 flag.py                 # echoes FLAG per the contract above
    python3 flag.py --secret        # also prints the guarded SIGMA value
    # legacy/local-dev (off-arena), still supported for compatibility:
    TEAM_SECRET=<team-secret> python3 flag.py
    python3 flag.py <team-secret>
    python3 flag.py <team-secret> --secret
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "ai-ai2-output-filter"

# Local-dev only. On the arena FLAG / CHALLENGE_SECRET are injected and this is
# never consulted; it only lets the challenge run off-arena.
_DEV_TEAM_SECRET = "local-dev-secret"


def _hmac_hex(key: str, label: str) -> str:
    return hmac.new(key.encode(), label.encode(), hashlib.sha256).hexdigest()


# ---- legacy per-team derivations (kept for compatibility) -----------------
def flag(team_secret: str) -> str:
    """Legacy: reproduce the flag from a team master secret (local dev only)."""
    return "CTF{" + _hmac_hex(team_secret, CHALLENGE_ID)[:24] + "}"


def guarded_secret(team_secret: str) -> str:
    """Legacy: reproduce the guarded SIGMA value from a team master secret."""
    return "SIGMA-" + _hmac_hex(team_secret, CHALLENGE_ID + ":guarded")[:16]


# ---- new per-challenge contract -------------------------------------------
def get_challenge_secret() -> str:
    """The per-challenge secret CHALLENGE_SECRET.

    On the arena this is injected. Off-arena it is reconstructed from the dev
    TEAM_SECRET fallback (CHALLENGE_SECRET == HMAC(team_secret, CHALLENGE_ID)),
    so local runs still work without TEAM_SECRET being injected.
    """
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return cs
    # LOCAL DEV fallback -- not used on the arena.
    return _hmac_hex(os.environ.get("TEAM_SECRET", _DEV_TEAM_SECRET), CHALLENGE_ID)


def get_flag() -> str:
    """The flag, per the per-challenge contract.

    Order: FLAG env var; else CHALLENGE_SECRET[:24]; else a LOCAL DEV fallback
    derived from the dev TEAM_SECRET so the challenge still runs off-arena.
    """
    f = os.environ.get("FLAG")
    if f:
        return f
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return "CTF{" + cs[:24] + "}"
    # LOCAL DEV fallback -- not used on the arena.
    return flag(os.environ.get("TEAM_SECRET", _DEV_TEAM_SECRET))


def get_guarded_secret() -> str:
    """The guarded SIGMA value, derived from CHALLENGE_SECRET (aux secret)."""
    return "SIGMA-" + _hmac_hex(get_challenge_secret(), "guarded")[:16]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--secret"]
    show_secret = "--secret" in sys.argv[1:]

    if args:
        # Legacy path: an explicit team secret was passed on argv.
        team_secret = args[0]
        print(flag(team_secret))
        if show_secret:
            print(guarded_secret(team_secret))
    else:
        # Contract path: echo FLAG (from env, CHALLENGE_SECRET, or dev fallback).
        print(get_flag())
        if show_secret:
            print(get_guarded_secret())
