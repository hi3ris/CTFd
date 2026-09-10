#!/usr/bin/env python3
"""Per-team dynamic flag derivation for misc-proto-fuzz.

The platform instancier starts one container PER TEAM and injects that team's
secret via the TEAM_SECRET environment variable. The flag is derived
deterministically from that secret and the fixed challenge id, so the scoreboard
can recompute and validate a team's flag without the flag ever living in a
downloadable artifact.

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "misc-proto-fuzz")[:24] + "}"

The [:24] slice takes the first 24 hex characters of the hex digest.

The FZLP service (server.py) imports this to compute the flag it will emit ONLY
after it observes the required effect (the hidden maintenance channel becoming
armed via the CFG length off-by-one). It is also runnable standalone for the
platform's validation tooling:

    TEAM_SECRET=deadbeef python3 flag.py
"""
import hmac
import hashlib
import os

CHALLENGE_ID = "misc-proto-fuzz"


def derive_flag(team_secret: str) -> str:
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "CTF{" + digest[:24] + "}"


def get_flag() -> str:
    # Fall back to a clearly-marked local value so the service still runs
    # outside the arena (local dev / playtest). Real instances always get a
    # per-team TEAM_SECRET from the instancier.
    secret = os.environ.get("TEAM_SECRET", "local-dev-secret")
    return derive_flag(secret)


if __name__ == "__main__":
    print(get_flag())
