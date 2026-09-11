#!/usr/bin/env python3
"""Per-challenge dynamic flag resolution for ml-pickle-rce.

The instancier injects per-challenge values into the container:

    FLAG              the exact flag string, e.g. "NCTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e. FLAG == "NCTF{" + CHALLENGE_SECRET[:24] + "}"

The flag VALUE is unchanged from the old TEAM_SECRET-based scheme: the old flag
was

    flag = "NCTF{" + HMAC_SHA256(TEAM_SECRET, "ml-pickle-rce")[:24] + "}"

and the instancier now sets CHALLENGE_SECRET == HMAC_SHA256(team_secret,
"ml-pickle-rce"), so CHALLENGE_SECRET[:24] is exactly the old flag body. The
scoreboard's team_hmac flag class validates the same value. Owning one container
now leaks only this challenge's flag, not the team master secret.

entrypoint.sh uses this module to write THIS instance's FLAG into a file on the
service host (default /flag). The registry service never returns that file; a
solver only gets it by executing code during unpickling and reading it. This
module is also runnable standalone for the platform's validation tooling:

    CHALLENGE_SECRET=deadbeef... python3 flag.py
    FLAG='NCTF{...}'              python3 flag.py
"""
import hmac
import hashlib
import os

CHALLENGE_ID = "ml-pickle-rce"


def derive_flag(team_secret: str) -> str:
    """Compat: derive the flag from a raw team secret (old scheme).

    Kept so the old derivation is still available to tooling. Runtime no longer
    depends on this: real instances receive FLAG / CHALLENGE_SECRET directly.
    """
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "NCTF{" + digest[:24] + "}"


def get_flag() -> str:
    # 1) Instancier injects the exact flag string.
    flag = os.environ.get("FLAG")
    if flag:
        return flag

    # 2) Instancier injects the per-challenge secret; the flag body is its
    #    first 24 hex chars. CHALLENGE_SECRET == HMAC(team_secret, CHALLENGE_ID),
    #    so this reproduces the old flag value exactly.
    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "NCTF{" + challenge_secret[:24] + "}"

    # 3) LOCAL DEV fallback (off-arena only). Derive a CHALLENGE_SECRET from the
    #    TEAM_SECRET dev default the same way the instancier would, then take its
    #    first 24 hex chars -- identical to the old dev flag value.
    dev_challenge_secret = hmac.new(
        os.environ.get("TEAM_SECRET", "local-dev-secret").encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "NCTF{" + dev_challenge_secret[:24] + "}"


if __name__ == "__main__":
    print(get_flag())
