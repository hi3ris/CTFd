#!/usr/bin/env python3
"""Per-challenge flag derivation for `sysadmin-orchestrator-cap` (served, per-team).

The instancier injects FLAG / CHALLENGE_SECRET; the flag body is
CHALLENGE_SECRET[:24], i.e. FLAG == "NCTF{" + CHALLENGE_SECRET[:24] + "}".
Off-arena, a LOCAL DEV fallback derives from TEAM_SECRET so the image still runs.
"""
import hashlib
import hmac
import os
import sys

CHALLENGE_ID = "sysadmin-orchestrator-cap"


def flag(team_secret: str) -> str:
    digest = hmac.new(
        team_secret.encode(), CHALLENGE_ID.encode(), hashlib.sha256
    ).hexdigest()
    return "NCTF{" + digest[:24] + "}"


def get_flag() -> str:
    env_flag = os.environ.get("FLAG")
    if env_flag:
        return env_flag
    cs = os.environ.get("CHALLENGE_SECRET")
    if cs:
        return "NCTF{" + cs[:24] + "}"
    return flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    print(flag(sys.argv[1]) if len(sys.argv) > 1 else get_flag())
