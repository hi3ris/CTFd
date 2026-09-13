#!/usr/bin/env python3
"""
Per-challenge flag derivation for challenge `ml-model-inversion`.

The per-team instancer injects PER-CHALLENGE values into the served container
(it does NOT inject the team MASTER secret, so owning one container does not
leak every flag for the team):

    FLAG              the exact flag string, e.g. "NCTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24]
                      i.e. FLAG == "NCTF{" + CHALLENGE_SECRET[:24] + "}"

The flag VALUE matches the scoreboard's team_hmac flag class:
    flag = "NCTF{" + HMAC_SHA256(TEAM_SECRET, "ml-model-inversion")[:24] + "}"
and the instancer sets CHALLENGE_SECRET = HMAC(team_secret, CHALLENGE_ID), so
CHALLENGE_SECRET[:24] is exactly that flag body.

The memorised record the player must invert is a SEPARATE projection of the same
secret (see app/model.py derive_record); it is independent of the flag body, so
neither reveals the other.

Usage (arena):    the container already has FLAG / CHALLENGE_SECRET in env
Usage (local dev): TEAM_SECRET=<team-secret> python3 flag.py
                   python3 flag.py <team-secret>
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "ml-model-inversion"


def flag(team_secret: str) -> str:
    dig = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()
    return "NCTF{" + dig[:24] + "}"


def get_flag() -> str:
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return "NCTF{" + cs[:24] + "}"
    return flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(flag(sys.argv[1]))
    else:
        print(get_flag())
