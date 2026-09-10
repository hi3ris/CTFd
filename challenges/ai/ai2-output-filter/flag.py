#!/usr/bin/env python3
"""
Per-team flag derivation for challenge `ai-ai2-output-filter`.

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "ai-ai2-output-filter")[:24] + "}"

The platform injects TEAM_SECRET into the container at creation time; feeding
the same value here reproduces the flag CTFd should accept for that team.

The SIGMA value the model guards is a DIFFERENT derivation from the same
TEAM_SECRET (label "ai-ai2-output-filter:guarded"); it is intentionally NOT the
flag -- a player recovers it past the output filter and submits it to /verify,
which returns the flag above. Pass --secret to print the guarded value too
(useful for platform smoke tests). These derivations match app.py exactly.

Usage:
    TEAM_SECRET=<team-secret> python3 flag.py
    python3 flag.py <team-secret>
    python3 flag.py <team-secret> --secret
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "ai-ai2-output-filter"


def _hmac_hex(team_secret: str, label: str) -> str:
    return hmac.new(team_secret.encode(), label.encode(), hashlib.sha256).hexdigest()


def flag(team_secret: str) -> str:
    return "CTF{" + _hmac_hex(team_secret, CHALLENGE_ID)[:24] + "}"


def guarded_secret(team_secret: str) -> str:
    return "SIGMA-" + _hmac_hex(team_secret, CHALLENGE_ID + ":guarded")[:16]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--secret"]
    show_secret = "--secret" in sys.argv[1:]
    secret = args[0] if args else os.environ.get("TEAM_SECRET")
    if not secret:
        sys.exit("provide TEAM_SECRET (env var or argv[1])")
    print(flag(secret))
    if show_secret:
        print(guarded_secret(secret))
