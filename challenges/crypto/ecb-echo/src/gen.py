#!/usr/bin/env python3
"""Deterministic generator for the 'ecb-echo' challenge.

Models a service that encrypts  AES-ECB( attacker_input || SECRET )  under one
fixed key, where SECRET is the flag. We tap the service and record a raw oracle
transcript so the player can mount a genuine byte-at-a-time recovery offline:

* `probe`: ciphertext for input "A"*k, k = 0..32, so the block size and the
  secret length can be recovered from where the ciphertext length jumps.
* `queries`: a raw query->ciphertext transcript. Each key is a *fingerprint*
  (SHA-256) of one attacker input the player-style attacker would send; the
  value is the full ciphertext hex the device produced for it. The transcript
  is unlabelled: it does not say which query targets which secret position, nor
  which ciphertext block is the answer. To read a byte the solver must build the
  right aligned filler, then, for each printable guess, build
  `filler || recovered_so_far || guess`, fingerprint it, look up the ciphertext
  and compare the aligned block against the filler-only ciphertext's block. The
  next-byte fingerprint only exists once the previous byte is recovered, so the
  attack chains and must actually be performed -- there is no precomputed
  candidate->answer map, and no secret plaintext is stored anywhere in the log.
"""
import hashlib
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


def fp(attacker: bytes) -> str:
    return hashlib.sha256(attacker).hexdigest()


def main() -> None:
    probe = [oracle(b"A" * k).hex() for k in range(2 * B + 1)]

    queries = {}
    for i in range(len(FLAG)):
        pad = B - 1 - (i % B)
        prefix = b"A" * pad
        # Filler-only query the solver aligns and slices to derive the target.
        queries[fp(prefix)] = oracle(prefix).hex()
        # One query per printable guess: filler || known secret prefix || guess.
        # Only the correct running prefix reproduces the aligned target block.
        for c in range(0x20, 0x7F):
            inp = prefix + FLAG[:i] + bytes([c])
            queries[fp(inp)] = oracle(inp).hex()

    transcript = {"probe": probe, "queries": queries}
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "oracle_log.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(transcript, fh)
        fh.write("\n")
    print(
        f"wrote oracle_log.json ({os.path.getsize(out)} bytes, "
        f"{len(queries)} queries)"
    )


if __name__ == "__main__":
    main()
