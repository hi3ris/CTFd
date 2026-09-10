#!/usr/bin/env python3
"""Per-challenge flag derivation for pwn-heap-note.

The per-team instancier now injects PER-CHALLENGE values into the container
instead of the team MASTER secret. Owning one container therefore only ever
exposes this one challenge's flag, never the whole team's.

Runtime contract (what the instancier injects):

    FLAG              the exact flag string, e.g. "CTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "CTF{" + CHALLENGE_SECRET[:24] + "}"

TEAM_SECRET is NO LONGER injected. The flag VALUE is unchanged: previously the
flag was "CTF{" + HMAC_SHA256(TEAM_SECRET, CHALLENGE_ID)[:24] + "}", and the
instancier now sets CHALLENGE_SECRET == HMAC_SHA256(team_secret, CHALLENGE_ID),
so CHALLENGE_SECRET[:24] is exactly the old flag body. The scoreboard's
team_hmac flag class validates the same value.

entrypoint.sh uses this module to compute the FLAG exported to the served
binary (win() prints getenv("FLAG")). It is also runnable standalone for the
platform's validation tooling:

    CHALLENGE_SECRET=deadbeef... python3 flag.py
    FLAG='CTF{...}'             python3 flag.py
"""
import hmac
import hashlib
import os

CHALLENGE_ID = "pwn-heap-note"


def derive_flag(team_secret: str) -> str:
    """LOCAL DEV ONLY: reproduce the flag from a team master secret.

    Kept for compatibility with off-arena tooling. Production never calls this;
    real instances get FLAG / CHALLENGE_SECRET straight from the instancier.
    """
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "CTF{" + digest[:24] + "}"


def get_flag() -> str:
    """Return this instance's flag, following the runtime contract in order.

    1. FLAG, if the instancier injected it -> returned verbatim.
    2. else CHALLENGE_SECRET -> "CTF{" + CHALLENGE_SECRET[:24] + "}".
    3. else a clearly-marked LOCAL DEV fallback derived from the TEAM_SECRET dev
       value, so the service still runs off-arena (local dev / playtest).
    """
    flag = os.environ.get("FLAG")
    if flag:
        return flag

    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "CTF{" + challenge_secret[:24] + "}"

    # LOCAL DEV fallback -- never hit in the arena (instancier always injects
    # FLAG and CHALLENGE_SECRET). Derived from the TEAM_SECRET dev value so
    # local runs and old playtest tooling keep working.
    return derive_flag(os.environ.get("TEAM_SECRET", "local-dev-secret"))


if __name__ == "__main__":
    print(get_flag())
