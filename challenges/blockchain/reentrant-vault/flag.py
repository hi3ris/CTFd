#!/usr/bin/env python3
"""Per-challenge flag derivation for blockchain-reentrant-vault.

Same per-team contract as the other served challenges: the instancier injects
FLAG / CHALLENGE_SECRET; flag body = CHALLENGE_SECRET[:24]. The flag is revealed
only by the launcher's /flag endpoint once the vault is drained; it is never on
chain and never baked into the image.
"""
import hashlib
import hmac
import os

CHALLENGE_ID = "blockchain-reentrant-vault"


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
