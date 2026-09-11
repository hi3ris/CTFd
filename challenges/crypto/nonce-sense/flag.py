#!/usr/bin/env python3
"""
Flag derivation for 'nonce-sense' (crypto-nonce-sense).

This is a pure downloadable challenge with a STATIC flag (no served oracle, so
no per-team TEAM_SECRET / HMAC flag is used -- see the authoring rules). The
flag is a deterministic function of the private key d that the capture leaks:

    flag = "NCTF{" + sha256( "%064x" % d )[:32] + "}"

Running this file with the known private key reproduces the flag stored in
challenge.yml, so the platform / author can validate it.
"""
import hashlib, sys

CHALLENGE_ID = "crypto-nonce-sense"

# The private key baked into the shipped capture.json (author record).
D = 0x690ba66683c56d39767739a1d314a86adea774001ead3aaceb43fb0304a338cb

def flag_for_key(d: int) -> str:
    return "NCTF{" + hashlib.sha256(("%064x" % d).encode()).hexdigest()[:32] + "}"

if __name__ == "__main__":
    d = int(sys.argv[1], 0) if len(sys.argv) > 1 else D
    print(flag_for_key(d))
