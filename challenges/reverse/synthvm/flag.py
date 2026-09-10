#!/usr/bin/env python3
"""
flag.py for reverse/synthvm.

This is a STATIC downloadable reverse-engineering challenge: the artifact
(./synthvm) carries the flag logic locally, which the guardrails explicitly
allow for RE. There is no served container and no per-team secret, so the
per-team HMAC scheme is NOT used here; the flag is static and also lives in
challenge.yml.

The flag equals the exact input the embedded bytecode accepts. It is never
stored in plaintext in the binary - only its transformed image is. This script
prints the static flag for platform tooling; solution/solve.py demonstrates how
it is actually recovered from the artifact by disassembly + inversion.
"""

CHALLENGE_ID = "reverse-synthvm"
FLAG = "CTF{synthvm_d1sp4tch_rem4pped_at_runtime}"


def get_flag(team_secret: str | None = None) -> str:
    # Static challenge: the flag does not depend on TEAM_SECRET.
    return FLAG


if __name__ == "__main__":
    print(FLAG)
