#!/usr/bin/env python3
"""Per-challenge flag derivation for pwn-boot2root-linux.

The per-team instancier injects PER-CHALLENGE values into each container (it no
longer injects the team MASTER secret, so owning one container never exposes
other challenges' flags):

    FLAG              the exact flag string, e.g. "NCTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "NCTF{" + CHALLENGE_SECRET[:24] + "}"

entrypoint.sh uses this module to compute the FLAG it writes to /root/flag
(mode 400, root-owned). The flag is never baked into the image and never made
world-readable: it exists only in the instance's environment and in a file only
root can read, so the player must actually escalate to root to see it.

The flag VALUE is unchanged from the old scheme: previously
    flag = "NCTF{" + HMAC_SHA256(TEAM_SECRET, CHALLENGE_ID)[:24] + "}"
and the instancier now sets CHALLENGE_SECRET == HMAC_SHA256(team_secret,
CHALLENGE_ID), so CHALLENGE_SECRET[:24] is exactly the old flag body. The
scoreboard's team_hmac flag class validates the same value.

Runnable standalone for the platform's validation tooling:

    FLAG=NCTF{...}                python3 flag.py   # echoes FLAG verbatim
    CHALLENGE_SECRET=deadbeef...  python3 flag.py   # -> NCTF{deadbeef...[:24]}
    TEAM_SECRET=deadbeef          python3 flag.py   # LOCAL DEV fallback only
"""
import hmac
import hashlib
import os

CHALLENGE_ID = "pwn-boot2root-linux"


def derive_flag(team_secret: str) -> str:
    """LOCAL DEV ONLY: reproduce the flag from a team master secret.

    In the arena the flag body is CHALLENGE_SECRET[:24] and
    CHALLENGE_SECRET == HMAC(team_secret, CHALLENGE_ID), so this reproduces the
    exact same value when handed the team secret. Kept for off-arena runs and
    for backward compatibility with tooling that imports it.
    """
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "NCTF{" + digest[:24] + "}"


# Backwards-compatible alias for older callers that imported flag(secret).
flag = derive_flag


def get_flag() -> str:
    """Return this instance's flag under the per-challenge contract.

    Resolution order:
      1. FLAG env var, if set -> returned verbatim (the exact flag string).
      2. CHALLENGE_SECRET env var, if set -> "NCTF{" + CHALLENGE_SECRET[:24] + "}".
      3. LOCAL DEV fallback: derive from TEAM_SECRET (default "local-dev-secret")
         so the service still runs off-arena during playtesting.
    """
    flag_env = os.environ.get("FLAG")
    if flag_env:
        return flag_env

    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "NCTF{" + challenge_secret[:24] + "}"

    # LOCAL DEV fallback -- never hit in the arena (the instancier always
    # injects FLAG and CHALLENGE_SECRET).
    return derive_flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    print(get_flag())
