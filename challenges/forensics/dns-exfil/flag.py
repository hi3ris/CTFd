#!/usr/bin/env python3
"""
flag.py for forensics-dns-exfil.

This challenge is a STATIC, downloadable artifact (the pcap carries the answer),
so the authoritative flag lives in challenge.yml and inside the captured stream:

    NCTF{cu570m_b32_dns_tunn3l_r34ss3mbl3d}

The helper below is provided so the platform's tooling stays uniform:

  1. `python3 flag.py` prints the static flag (for validation import).

  2. `python3 flag.py <TEAM_SECRET>` shows the per-team HMAC flag that WOULD be
     used if this challenge were ever served per team, following the standard
     scheme:

         flag = "NCTF{" + HMAC_SHA256(TEAM_SECRET, CHALLENGE_ID)[:24] + "}"

     A served variant would need build/generate.py re-run with the note's
     recovery_token set to that HMAC digest; the static build here does not.
"""
import hashlib
import hmac
import sys

CHALLENGE_ID = "forensics-dns-exfil"
STATIC_FLAG = "NCTF{cu570m_b32_dns_tunn3l_r34ss3mbl3d}"


def team_flag(team_secret: str) -> str:
    digest = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(),
                      hashlib.sha256).hexdigest()
    return "NCTF{" + digest[:24] + "}"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(team_flag(sys.argv[1]))
    else:
        print(STATIC_FLAG)
