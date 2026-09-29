#!/usr/bin/env python3
"""Per-challenge flag derivation for pwn-boot2root-ssh (same contract as the
other served challenges). entrypoint.sh plants the flag at /root/flag (root:root
400) and scrubs the injected secrets; it is never baked into the image."""
import hashlib
import hmac
import os

CHALLENGE_ID = "pwn-boot2root-ssh"


def derive_flag(team_secret: str) -> str:
    digest = hmac.new(
        team_secret.encode("utf-8"), CHALLENGE_ID.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return "NCTF{" + digest[:24] + "}"


flag = derive_flag


def get_flag() -> str:
    if os.environ.get("FLAG"):
        return os.environ["FLAG"]
    if os.environ.get("CHALLENGE_SECRET"):
        return "NCTF{" + os.environ["CHALLENGE_SECRET"][:24] + "}"
    return derive_flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    print(get_flag())
