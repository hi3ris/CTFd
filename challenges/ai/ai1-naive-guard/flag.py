#!/usr/bin/env python3
"""
Per-team flag derivation for challenge `ai-ai1-naive-guard`.

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "ai-ai1-naive-guard")[:24] + "}"

The platform injects TEAM_SECRET into the container at creation time; the same
value fed here reproduces the flag CTFd should accept for that team.

The SIGMA secret the model guards is a DIFFERENT derivation from the same
TEAM_SECRET (label "ai-ai1-naive-guard/guard-secret"); it is intentionally not
the flag. Pass --secret to print it too (useful for platform smoke tests).

Usage:
    TEAM_SECRET=<team-secret> python3 flag.py
    python3 flag.py <team-secret>
    python3 flag.py <team-secret> --secret
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "ai-ai1-naive-guard"


def _hmac_hex(team_secret: str, label: str) -> str:
    return hmac.new(team_secret.encode(), label.encode(), hashlib.sha256).hexdigest()


def flag(team_secret: str) -> str:
    return "CTF{" + _hmac_hex(team_secret, CHALLENGE_ID)[:24] + "}"


def guard_secret(team_secret: str) -> str:
    h = _hmac_hex(team_secret, CHALLENGE_ID + "/guard-secret")[:16].upper()
    return f"SIGMA-{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--secret"]
    show_secret = "--secret" in sys.argv[1:]
    secret = args[0] if args else os.environ.get("TEAM_SECRET")
    if not secret:
        sys.exit("provide TEAM_SECRET (env var or argv[1])")
    print(flag(secret))
    if show_secret:
        print(guard_secret(secret))
