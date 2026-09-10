#!/usr/bin/env python3
"""
Per-team flag derivation for challenge `web-graphql-introspection-maze`.

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "web-graphql-introspection-maze")[:24] + "}"

The platform injects TEAM_SECRET into the container at creation time; the same
value fed here reproduces the flag CTFd should accept for that team. The flag
is emitted by the running instance only after the privileged effect
(session clearance -> ROOT) has actually occurred.

Usage:
    TEAM_SECRET=<team-secret> python3 flag.py
    python3 flag.py <team-secret>
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "web-graphql-introspection-maze"


def flag(team_secret: str) -> str:
    digest = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256).hexdigest()
    return "CTF{" + digest[:24] + "}"


if __name__ == "__main__":
    secret = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEAM_SECRET")
    if not secret:
        sys.exit("provide TEAM_SECRET (env var or argv[1])")
    print(flag(secret))
