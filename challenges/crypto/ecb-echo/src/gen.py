#!/usr/bin/env python3
"""Deterministic generator for the 'ecb-echo' challenge.

Models a service that encrypts  AES-ECB( attacker_input || SECRET )  under one
fixed key, where SECRET is the flag. We capture the oracle's behaviour into a
static log so the player can mount a byte-at-a-time recovery offline:

* `probe`: ciphertext for input "A"*k, k = 0..32, so the block size and the
  secret length can be recovered from where the length jumps.
* `steps`: for each secret byte position, the ciphertext block observed for the
  aligned short input (`target`) plus, for every printable byte value, the
  ciphertext block that a guess would produce (`candidates`). Matching a
  candidate to the target reveals that secret byte.

No plaintext bytes of the secret are stored -- only ciphertext blocks.
"""
import json
import os

from Crypto.Cipher import AES

FLAG = b"NCTF{ecb_leaks_appended_secrets_one_byte_per_query}"

KEY = bytes.fromhex("8f2a41c0b9d7e6350a1c4d8e7f60b2a3")  # fixed device key
B = 16


def oracle(attacker: bytes) -> bytes:
    data = attacker + FLAG
    pad = (-len(data)) % B
    data = data + b"\x00" * pad
    return AES.new(KEY, AES.MODE_ECB).encrypt(data)


def block(ct: bytes, idx: int) -> bytes:
    return ct[idx * B : idx * B + B]


def main() -> None:
    probe = [oracle(b"A" * k).hex() for k in range(33)]

    steps = []
    for i in range(len(FLAG)):
        block_idx = i // B
        pad = B - 1 - (i % B)
        prefix = b"A" * pad
        target = block(oracle(prefix), block_idx).hex()
        candidates = {}
        for c in range(0x20, 0x7F):
            inp = prefix + FLAG[:i] + bytes([c])
            candidates[chr(c)] = block(oracle(inp), block_idx).hex()
        steps.append({"block": block_idx, "target": target, "candidates": candidates})

    transcript = {"probe": probe, "steps": steps}
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "oracle_log.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(transcript, fh)
        fh.write("\n")
    print(f"wrote oracle_log.json ({os.path.getsize(out)} bytes, {len(steps)} steps)")


if __name__ == "__main__":
    main()
