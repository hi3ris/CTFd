#!/usr/bin/env python3
"""
Reproduce the per-team dynamic flag so the platform can validate.

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "<challenge-id>")[:24] + "}"

Usage:
    TEAM_SECRET=... python3 flag.py
    python3 flag.py <team_secret>
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "web-ssrf-metadata-decoy"


def compute(team_secret: str) -> str:
    digest = hmac.new(
        team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256
    ).hexdigest()
    return "CTF{" + digest[:24] + "}"


if __name__ == "__main__":
    secret = os.environ.get("TEAM_SECRET")
    if secret is None and len(sys.argv) > 1:
        secret = sys.argv[1]
    if not secret:
        sys.exit("TEAM_SECRET not provided (env TEAM_SECRET=... or argv[1])")
    print(compute(secret))
