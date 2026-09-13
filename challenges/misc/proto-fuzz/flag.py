#!/usr/bin/env python3
"""Per-challenge dynamic flag resolution for misc-proto-fuzz.

The platform instancier starts one container PER TEAM and injects only
PER-CHALLENGE values, never the team master secret:

    FLAG              the exact flag string, e.g. "NCTF{<24 hex>}"
    CHALLENGE_SECRET  per-challenge hex; the flag body is CHALLENGE_SECRET[:24],
                      i.e.  FLAG == "NCTF{" + CHALLENGE_SECRET[:24] + "}"

Historically the flag was  "NCTF{" + HMAC_SHA256(TEAM_SECRET, CHALLENGE_ID)[:24] + "}",
and the instancier now computes CHALLENGE_SECRET == HMAC(team_secret, CHALLENGE_ID)
per challenge, so CHALLENGE_SECRET[:24] is exactly the old flag body. The value is
unchanged; only its source is. TEAM_SECRET is NO LONGER injected at runtime.

The FZLP service (server.py) imports get_flag() to compute the flag it emits ONLY
after it observes the required effect (the hidden maintenance channel becoming
armed via the CFG length off-by-one). get_flag() is also runnable standalone for
the platform's validation tooling:

    CHALLENGE_SECRET=deadbeef... python3 flag.py     # arena contract
    FLAG='NCTF{...}' python3 flag.py                  # explicit flag
    python3 flag.py                                  # LOCAL DEV fallback
"""
import hmac
import hashlib
import os

CHALLENGE_ID = "misc-proto-fuzz"

# Local-dev fallback ONLY. Never used in the arena: real instances always get
# FLAG or CHALLENGE_SECRET from the instancier. Kept so the image still runs
# off-arena (local dev / playtest) and reproduces the historical dev flag.
_DEV_TEAM_SECRET = "local-dev-secret"


def derive_flag(team_secret: str) -> str:
    """Legacy helper, kept for compatibility.

    Reproduces the historical derivation
        flag = "NCTF{" + HMAC_SHA256(team_secret, CHALLENGE_ID)[:24] + "}"
    which is equivalent to "NCTF{" + CHALLENGE_SECRET[:24] + "}" because
    CHALLENGE_SECRET == HMAC(team_secret, CHALLENGE_ID).
    """
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "NCTF{" + digest[:24] + "}"


def get_flag() -> str:
    """Resolve the flag per the per-challenge injection contract.

    Order:
      1. os.environ["FLAG"] if set (the exact flag string).
      2. else "NCTF{" + os.environ["CHALLENGE_SECRET"][:24] + "}".
      3. else a clearly-marked LOCAL DEV fallback derived from the dev
         TEAM_SECRET default, so the service still runs off-arena.
    """
    flag = os.environ.get("FLAG")
    if flag:
        return flag

    challenge_secret = os.environ.get("CHALLENGE_SECRET")
    if challenge_secret:
        return "NCTF{" + challenge_secret[:24] + "}"

    # LOCAL DEV fallback -- not an arena code path. Derive the dev
    # CHALLENGE_SECRET from the TEAM_SECRET dev default and slice it, which
    # equals the historical dev flag.
    dev_team_secret = os.environ.get("TEAM_SECRET", _DEV_TEAM_SECRET)
    dev_challenge_secret = hmac.new(
        dev_team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "NCTF{" + dev_challenge_secret[:24] + "}"


if __name__ == "__main__":
    print(get_flag())
