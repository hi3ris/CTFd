#!/usr/bin/env python3
"""Per-team dynamic flag derivation for web-race-the-coupon.

The platform injects a per-team secret into the container via the TEAM_SECRET
environment variable. The flag is derived deterministically from that secret and
the fixed challenge id, so the scoreboard can recompute and validate a team's
flag without the container ever writing it to a downloadable artifact.

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "web-race-the-coupon")[:24] + "}"

The [:24] slice takes the first 24 hex characters of the hex digest.
This module is imported by app.py; it is also runnable standalone for the
platform's validation tooling:

    TEAM_SECRET=deadbeef python3 flag.py
"""
import hmac
import hashlib
import os

CHALLENGE_ID = "web-race-the-coupon"


def derive_flag(team_secret: str) -> str:
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "CTF{" + digest[:24] + "}"


def get_flag() -> str:
    # Fall back to a clearly-marked local value so the app still runs outside
    # the arena (local dev / playtest). Real instances always get TEAM_SECRET.
    secret = os.environ.get("TEAM_SECRET", "local-dev-secret")
    return derive_flag(secret)


if __name__ == "__main__":
    print(get_flag())
