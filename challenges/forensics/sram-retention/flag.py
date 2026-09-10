#!/usr/bin/env python3
"""
`sram-retention` is a STATIC, downloadable forensics challenge: the artifact IS
the memory dump, so the flag is baked into the bytes of retention.dump and lives
in challenge.yml. There is no served container and therefore no per-team secret.

This file exists only to document, uniformly with the served challenges, how a
per-team dynamic flag WOULD be derived if this challenge were ever served. The
platform does not need it to validate this challenge.
"""

import hashlib
import hmac
import os

CHALLENGE_ID = "forensics-sram-retention"

# The static flag actually used by this challenge (see challenge.yml).
STATIC_FLAG = "CTF{sram_retention_bank_interleave}"


def derive_flag(team_secret: str, challenge_id: str = CHALLENGE_ID) -> str:
    """Per-team scheme used by served challenges (documented here for uniformity)."""
    digest = hmac.new(
        team_secret.encode(), challenge_id.encode(), hashlib.sha256
    ).hexdigest()
    return "CTF{" + digest[:24] + "}"


if __name__ == "__main__":
    secret = os.environ.get("TEAM_SECRET")
    if secret:
        print(derive_flag(secret))
    else:
        print(STATIC_FLAG)
