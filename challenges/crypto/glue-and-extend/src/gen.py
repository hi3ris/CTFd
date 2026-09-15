#!/usr/bin/env python3
"""Deterministic generator for the 'glue-and-extend' challenge.

A service seals payloads under key = SHA256(secret || command). We capture:

* an authorized command and its tag  tag1 = SHA256(secret || command1),
* a sealed flag payload for an *elevated* command that the service built by
  appending an admin suffix -- with the SHA-256 glue padding kept in between, so
  the sealed command is exactly  command1 || glue || suffix.

Because SHA-256 is a Merkle-Damgard hash, tag1 lets an attacker who does not
know the secret continue the hash and reproduce the elevated tag, hence the
sealing key.
"""
import hashlib
import os
import random

FLAG = b"NCTF{merkle_damgard_length_extension_forges_the_tag}"

COMMAND1 = b"user=guest&action=list&ts=1700000000"
SUFFIX = b"&action=export&target=flag"


def md_padding(msg_len: int) -> bytes:
    """SHA-256 padding bytes for a message of `msg_len` bytes."""
    pad = b"\x80"
    pad += b"\x00" * ((56 - (msg_len + 1) % 64) % 64)
    pad += (msg_len * 8).to_bytes(8, "big")
    return pad


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def main() -> None:
    rng = random.Random(0xBADC0DE)
    secret = bytes(rng.getrandbits(8) for _ in range(17))

    tag1 = hashlib.sha256(secret + COMMAND1).digest()

    glue = md_padding(len(secret) + len(COMMAND1))
    elevated = secret + COMMAND1 + glue + SUFFIX
    elevated_tag = hashlib.sha256(elevated).digest()

    sealed = bytes(a ^ b for a, b in zip(FLAG, keystream(elevated_tag, len(FLAG))))

    transcript = [
        f"COMMAND={COMMAND1.decode()}",
        f"TAG={tag1.hex()}",
        f"SUFFIX={SUFFIX.decode()}",
        f"SEALED={sealed.hex()}",
    ]
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "token.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(transcript) + "\n")
    print("wrote token.txt (secret length was", len(secret), "-- not shipped)")


if __name__ == "__main__":
    main()
