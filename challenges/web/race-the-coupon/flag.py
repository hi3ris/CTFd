#!/usr/bin/env python3
"""Per-challenge dynamic flag derivation for web-race-the-coupon.

The platform instancier injects per-challenge values into each container:

    FLAG              the exact flag string, e.g. "CTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "CTF{" + CHALLENGE_SECRET[:24] + "}"

The flag is a deterministic per-challenge value the scoreboard can recompute and
validate without the container ever writing it to a downloadable artifact.
Historically the flag body was HMAC_SHA256(TEAM_SECRET, CHALLENGE_ID)[:24], and
CHALLENGE_SECRET == HMAC_SHA256(team_secret, CHALLENGE_ID), so
CHALLENGE_SECRET[:24] is exactly that same body -- the flag VALUE is unchanged.

TEAM_SECRET is no longer injected at runtime; it is only consulted as a
LOCAL DEV fallback so the app still runs off-arena (local dev / playtest).

This module is imported by app.py; it is also runnable standalone for the
platform's validation tooling:

    FLAG=CTF{...} python3 flag.py
    CHALLENGE_SECRET=deadbeef... python3 flag.py
    TEAM_SECRET=deadbeef python3 flag.py   # local dev only
"""
import hmac
import hashlib
import os

CHALLENGE_ID = "web-race-the-coupon"


def derive_flag(team_secret: str) -> str:
    """Compatibility helper: original TEAM_SECRET-based derivation.

    Retained so any existing tooling that calls it keeps working. The service
    and __main__ go through get_flag(), which reads the new contract.
    """
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "CTF{" + digest[:24] + "}"


# Backwards-compatible alias for any caller expecting flag(secret).
flag = derive_flag


def get_flag() -> str:
    # 1. Exact flag string injected by the instancier.
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag

    # 2. Per-challenge secret injected by the instancier: flag body is [:24].
    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "CTF{" + challenge_secret[:24] + "}"

    # 3. LOCAL DEV fallback ONLY. Not used in the arena. Derives the same value
    #    the old contract would have produced from TEAM_SECRET, so local runs
    #    and playtests still work off-arena.
    dev_secret = os.environ.get("TEAM_SECRET", "local-dev-secret")
    return derive_flag(dev_secret)


if __name__ == "__main__":
    print(get_flag())
