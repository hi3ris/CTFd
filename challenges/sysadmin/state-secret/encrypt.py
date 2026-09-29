#!/usr/bin/env python3
"""Vault blob encryptor for the Terraform bundle (shipped with the handout).

This is the exact program ``main.tf`` invokes (as a ``data.external`` source) to
turn a plaintext secret into the ``vault.enc`` blob. It is included with the
challenge on purpose: the blob format is fully documented here, so anyone
holding the passphrase can invert it. Pure standard library.

Blob format (all fields concatenated, no separators):

    magic       4 bytes   ASCII "ENC1"
    salt        16 bytes  random per-encryption, stored in the clear
    iters       4 bytes   PBKDF2 iteration count, unsigned big-endian
    ciphertext  N bytes   len == len(plaintext)

Key schedule and cipher (a stdlib-only stream cipher):

    key    = PBKDF2-HMAC-SHA256(passphrase, salt, iters)      # 32-byte key
    stream = SHA256(key || counter_be64) for counter = 0, 1, 2, ...
             (concatenated, truncated to len(ciphertext))
    ct[i]  = pt[i] XOR stream[i]        # and pt[i] = ct[i] XOR stream[i]

Decryption is symmetric: rebuild the same keystream and XOR again. See the
reference decryptor in ``solution/solve.py``.

Usage:
  * As a Terraform external data program (reads a JSON object on stdin with
    keys ``passphrase`` and ``infile``; writes ``vault.enc`` next to this file
    and prints ``{"path": "vault.enc"}``):
        echo '{"passphrase":"...","infile":"secret.txt"}' | python3 encrypt.py
  * Directly, for manual use:
        python3 encrypt.py <passphrase> <infile> <outfile>
"""

import hashlib
import json
import os
import sys

MAGIC = b"ENC1"
DEFAULT_ITERS = 50000


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(8, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def encrypt(
    passphrase: str, plaintext: bytes, salt: bytes, iters: int = DEFAULT_ITERS
) -> bytes:
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, iters)
    ct = bytes(a ^ b for a, b in zip(plaintext, keystream(key, len(plaintext))))
    return MAGIC + salt + iters.to_bytes(4, "big") + ct


def decrypt(passphrase: str, blob: bytes) -> bytes:
    if blob[:4] != MAGIC:
        raise ValueError("bad magic")
    salt = blob[4:20]
    iters = int.from_bytes(blob[20:24], "big")
    ct = blob[24:]
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, iters)
    return bytes(a ^ b for a, b in zip(ct, keystream(key, len(ct))))


def _as_external_program() -> None:
    query = json.load(sys.stdin)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, query["infile"]), "rb") as fh:
        plaintext = fh.read()
    salt = os.urandom(16)
    blob = encrypt(query["passphrase"], plaintext, salt)
    with open(os.path.join(here, "vault.enc"), "wb") as fh:
        fh.write(blob)
    json.dump({"path": "vault.enc"}, sys.stdout)


def main() -> None:
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        _as_external_program()
        return
    if len(sys.argv) == 4:
        passphrase, infile, outfile = sys.argv[1:]
        with open(infile, "rb") as fh:
            plaintext = fh.read()
        with open(outfile, "wb") as fh:
            fh.write(encrypt(passphrase, plaintext, os.urandom(16)))
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
