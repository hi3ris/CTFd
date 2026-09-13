#!/usr/bin/env python3
"""
flag.py for forensics-usb-keystrokes.

This challenge is a STATIC, downloadable artifact (the pcap carries the answer),
so the authoritative flag lives in challenge.yml:

    NCTF{Bl4ck_H4t_USB_2026}

The helper below is provided for two reasons:

  1. `python3 flag.py` prints the static flag, so the platform can validate it.

  2. `python3 flag.py <TEAM_SECRET>` shows the per-team HMAC flag that WOULD be
     used if this challenge were ever served per team. It follows the standard
     scheme so the platform's tooling stays uniform:

         flag = "NCTF{" + HMAC_SHA256(TEAM_SECRET, CHALLENGE_ID)[:24] + "}"

     Note: a served variant would need a regenerated pcap whose typed passphrase
     equals that HMAC digest; the static build here does not use it.
"""
import hashlib
import hmac
import sys

CHALLENGE_ID = "forensics-usb-keystrokes"
STATIC_FLAG = "NCTF{Bl4ck_H4t_USB_2026}"


def team_flag(team_secret: str) -> str:
    digest = hmac.new(team_secret.encode(), CHALLENGE_ID.encode(),
                      hashlib.sha256).hexdigest()
    return "NCTF{" + digest[:24] + "}"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(team_flag(sys.argv[1]))
    else:
        print(STATIC_FLAG)
