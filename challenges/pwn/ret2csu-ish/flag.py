#!/usr/bin/env python3
"""Per-challenge dynamic flag derivation for pwn-ret2csu-ish.

The platform instancier injects PER-CHALLENGE values into the container (it no
longer injects the team MASTER secret, so owning one container cannot leak every
flag for the team):

    FLAG              the exact flag string, e.g. "NCTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "NCTF{" + CHALLENGE_SECRET[:24] + "}"

CHALLENGE_SECRET is exactly HMAC_SHA256(team_secret, CHALLENGE_ID), so its first
24 hex characters are the same flag body the challenge produced before -- this
is a SOURCE change, not a value change. The scoreboard's team_hmac flag class
validates the identical value.

entrypoint.sh exports the derived value as FLAG into the environment of the
served process. Because the flag lives only in the process environment, a shell
(or any program) obtained through the ROP chain inherits it and can print it --
which is exactly the effect the challenge verifies. Reading the downloadable
binary can never yield a team's flag.

Runnable standalone for the platform's validation tooling:

    CHALLENGE_SECRET=deadbeef... python3 flag.py
    FLAG='NCTF{...}' python3 flag.py
    TEAM_SECRET=deadbeef python3 flag.py      # local dev fallback only
"""
import hmac
import hashlib
import os

CHALLENGE_ID = "pwn-ret2csu-ish"


def derive_flag(secret: str) -> str:
    """Compatibility shim: derive the flag body from a raw team secret.

    Kept so any external tooling that still calls flag(team_secret) keeps
    working. Runtime code goes through get_flag() instead.
    """
    digest = hmac.new(
        secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "NCTF{" + digest[:24] + "}"


# Back-compat alias: some tooling expects a function literally named flag().
flag = derive_flag


def get_flag() -> str:
    """Return this instance's flag under the new per-challenge contract.

    Resolution order:
      1. FLAG              -- exact flag injected by the instancier; use as-is.
      2. CHALLENGE_SECRET  -- per-challenge hex; flag = "NCTF{" + [:24] + "}".
      3. LOCAL DEV fallback -- derive CHALLENGE_SECRET from a dev TEAM_SECRET so
         the service still runs off-arena (local dev / playtest). Real instances
         always get FLAG or CHALLENGE_SECRET from the instancier.
    """
    flag_env = os.environ.get("FLAG")
    if flag_env:
        return flag_env

    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "NCTF{" + challenge_secret[:24] + "}"

    # LOCAL DEV FALLBACK ONLY -- not used in the arena. Reconstruct
    # CHALLENGE_SECRET == HMAC_SHA256(team_secret, CHALLENGE_ID) from the dev
    # TEAM_SECRET so the derived value matches the historical flag body.
    team_secret = os.environ.get("TEAM_SECRET", "local-dev-secret")
    dev_challenge_secret = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "NCTF{" + dev_challenge_secret[:24] + "}"


if __name__ == "__main__":
    print(get_flag())
