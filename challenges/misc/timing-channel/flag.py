#!/usr/bin/env python3
"""
flag.py for misc-timing-channel.

This challenge is a STATIC, downloadable artifact (the packet capture carries
the answer in its inter-arrival timing), so the authoritative flag lives in
challenge.yml and inside the capture itself:

    NCTF{silence_between_beats_speaks}

The helper below is provided so the platform's tooling stays uniform:

  1. `python3 flag.py` prints the static flag (for validation import).

  2. `python3 flag.py <TEAM_SECRET>` shows the per-team HMAC flag that WOULD be
     used if this challenge were ever served per team, following the standard
     scheme:

         flag = "NCTF{" + HMAC_SHA256(TEAM_SECRET, CHALLENGE_ID)[:24] + "}"

     A served variant would need gen.py re-run so the timing pattern spells that
     HMAC digest; the static build here does not.
"""
import hashlib
import hmac
import sys

CHALLENGE_ID = "misc-timing-channel"
STATIC_FLAG = "NCTF{silence_between_beats_speaks}"


def team_flag(team_secret: str) -> str:
    digest = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(),
                      hashlib.sha256).hexdigest()
    return "NCTF{" + digest[:24] + "}"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(team_flag(sys.argv[1]))
    else:
        print(STATIC_FLAG)
