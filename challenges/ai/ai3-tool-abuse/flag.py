#!/usr/bin/env python3
"""
Per-team flag derivation for challenge `ai-ai3-tool-abuse` (AI track, Level 3).

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "ai-ai3-tool-abuse")[:24] + "}"

The platform injects TEAM_SECRET into the container at creation time; feeding
the same value here reproduces the flag CTFd should accept for that team.

Unlike ai1, there is NO separate "guarded secret" to extract. The flag is not
present anywhere in the model's context. It is produced by the tool backend
*only after the player has driven the assistant into performing a protected
effect* (an approved change plus a production deploy of the `release-oracle`
service). See app/tools.py for the effect check. This script only mirrors the
flag math so the platform can validate submissions.

Usage:
    TEAM_SECRET=<team-secret> python3 flag.py
    python3 flag.py <team-secret>
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "ai-ai3-tool-abuse"


def _hmac_hex(team_secret: str, label: str) -> str:
    return hmac.new(team_secret.encode(), label.encode(), hashlib.sha256).hexdigest()


def flag(team_secret: str) -> str:
    return "CTF{" + _hmac_hex(team_secret, CHALLENGE_ID)[:24] + "}"


if __name__ == "__main__":
    secret = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEAM_SECRET")
    if not secret:
        sys.exit("provide TEAM_SECRET (env var or argv[1])")
    print(flag(secret))
