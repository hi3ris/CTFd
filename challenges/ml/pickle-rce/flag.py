#!/usr/bin/env python3
"""Per-team dynamic flag derivation for ml-pickle-rce.

The platform injects a per-team secret into the container via the TEAM_SECRET
environment variable. The flag is derived deterministically from that secret and
the fixed challenge id, so the scoreboard can recompute and validate a team's
flag without the flag ever appearing in a downloadable artifact.

    flag = "CTF{" + HMAC_SHA256(TEAM_SECRET, "ml-pickle-rce")[:24] + "}"

The [:24] slice takes the first 24 hex characters of the hex digest.

entrypoint.sh uses this module to write the per-team FLAG into a file on the
service host (default /flag). The registry service never returns that file; a
solver only gets it by executing code during unpickling and reading it. This
module is also runnable standalone for the platform's validation tooling:

    TEAM_SECRET=deadbeef python3 flag.py
"""
import hmac
import hashlib
import os

CHALLENGE_ID = "ml-pickle-rce"


def derive_flag(team_secret: str) -> str:
    digest = hmac.new(
        team_secret.encode("utf-8"),
        CHALLENGE_ID.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "CTF{" + digest[:24] + "}"


def get_flag() -> str:
    # Local dev / playtest fallback. Real instances always receive a per-team
    # TEAM_SECRET from the instancier.
    secret = os.environ.get("TEAM_SECRET", "local-dev-secret")
    return derive_flag(secret)


if __name__ == "__main__":
    print(get_flag())
