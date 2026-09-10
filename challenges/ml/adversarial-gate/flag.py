#!/usr/bin/env python3
"""
Per-team flag derivation for challenge `ml-adversarial-gate`.

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "ml-adversarial-gate")[:24] + "}"

The platform injects TEAM_SECRET into the served container at creation time;
feeding the same value here reproduces the flag CTFd should accept for that
team. The flag is emitted by the running instance only after /submit verifies
(server side) that the submitted badge is within L-inf epsilon of the DENIED
badge AND is classified GRANTED by the real model.

Usage:
    TEAM_SECRET=<team-secret> python3 flag.py
    python3 flag.py <team-secret>
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "ml-adversarial-gate"


def flag(team_secret: str) -> str:
    dig = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()
    return "CTF{" + dig[:24] + "}"


if __name__ == "__main__":
    secret = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEAM_SECRET")
    if not secret:
        sys.exit("provide TEAM_SECRET (env var or argv[1])")
    print(flag(secret))
