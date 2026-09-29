#!/usr/bin/env python3
"""Per-challenge flag derivation for supplychain-poisoned-pipeline.

Same per-team contract as the other served challenges: the instancier injects
FLAG / CHALLENGE_SECRET; flag body = CHALLENGE_SECRET[:24]. Here the flag is the
CI deploy secret (DEPLOY_TOKEN), injected only into deploy-stage steps and masked
from logs; it is never baked into the image.
"""
import hashlib
import hmac
import os

CHALLENGE_ID = "supplychain-poisoned-pipeline"


def derive_flag(team_secret: str) -> str:
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "NCTF{" + digest[:24] + "}"


flag = derive_flag


def get_flag() -> str:
    flag_env = os.environ.get("FLAG")
    if flag_env:
        return flag_env
    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "NCTF{" + challenge_secret[:24] + "}"
    return derive_flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    print(get_flag())
