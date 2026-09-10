#!/usr/bin/env python3
"""Per-challenge dynamic flag derivation for pwn-format-string-101.

The platform instancier injects PER-CHALLENGE values into each container:

    FLAG              the exact flag string, e.g. "CTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "CTF{" + CHALLENGE_SECRET[:24] + "}"

The instancier no longer injects the team MASTER secret (TEAM_SECRET), so owning
one container can no longer leak every flag for the team. The flag VALUE is
unchanged: previously flag = "CTF{" + HMAC(TEAM_SECRET, CHALLENGE_ID)[:24] + "}",
and CHALLENGE_SECRET == HMAC(team_secret, CHALLENGE_ID), so CHALLENGE_SECRET[:24]
is exactly the old flag body.

This module is used by entrypoint.sh to compute the FLAG passed to the served
binary. It is also runnable standalone for the platform's validation tooling:

    FLAG=CTF{...}       python3 flag.py   # echoes FLAG verbatim
    CHALLENGE_SECRET=ab python3 flag.py   # -> CTF{ab...[:24]}
    TEAM_SECRET=deadbeef python3 flag.py  # LOCAL DEV fallback only
"""
import hmac
import hashlib
import os

CHALLENGE_ID = "pwn-format-string-101"


def derive_flag(team_secret: str) -> str:
    """LOCAL DEV ONLY: reproduce the old derivation from a team secret.

    In the arena the flag body is CHALLENGE_SECRET[:24], and
    CHALLENGE_SECRET == HMAC(team_secret, CHALLENGE_ID), so this reproduces the
    exact same value when handed the team secret. Kept for off-arena runs and
    for backward compatibility with any tooling that imports it.
    """
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "CTF{" + digest[:24] + "}"


# Backwards-compatible alias for older callers that imported flag(secret).
flag = derive_flag


def get_flag() -> str:
    """Return this instance's flag under the per-challenge contract.

    Resolution order:
      1. FLAG env var, if set -> returned verbatim (the exact flag string).
      2. CHALLENGE_SECRET env var, if set -> "CTF{" + CHALLENGE_SECRET[:24] + "}".
      3. LOCAL DEV fallback: derive from TEAM_SECRET (default "local-dev-secret")
         so the service still runs off-arena during playtesting.
    """
    flag_env = os.environ.get("FLAG")
    if flag_env:
        return flag_env

    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "CTF{" + challenge_secret[:24] + "}"

    # LOCAL DEV fallback (never hit in the arena, where FLAG/CHALLENGE_SECRET
    # are always injected).
    return derive_flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    print(get_flag())
