#!/usr/bin/env python3
"""Reference solver for 'ecb-echo'.

The tapped service encrypts AES-ECB(attacker_input || SECRET). ECB is
deterministic and encrypts each 16-byte block independently, so by aligning the
next unknown secret byte as the last byte of a block and comparing against every
possible last byte, we recover the secret one byte at a time.

The shipped `oracle_log.json` is a raw, unlabelled transcript: `probe` gives the
ciphertext of "A"*k (to read the block size) and `queries` maps SHA-256(input)
-> ciphertext hex for the inputs a byte-at-a-time attacker would send. Nothing in
the log points at the answer, so we run the real attack: for each position we
build the aligned filler, derive the target block from the filler-only query,
then for each printable guess build `filler || recovered || guess`, look up its
ciphertext by fingerprint and compare the aligned block. The recovered prefix is
part of every guess input, so the log can only be used by actually performing
the recovery in order.
"""
import hashlib
import json
import os
import sys

B_MAX = 64  # sanity bound on block size


def fp(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def block(ct_hex: str, idx: int, bs: int) -> str:
    return ct_hex[idx * 2 * bs : (idx + 1) * 2 * bs]


def solve(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        log = json.load(fh)

    probe = log["probe"]
    queries = log["queries"]

    # Block size = the amount the ciphertext length jumps by as filler grows.
    lens = [len(h) // 2 for h in probe]
    block_size = next(
        lens[k + 1] - lens[k] for k in range(len(lens) - 1) if lens[k + 1] != lens[k]
    )
    assert 0 < block_size <= B_MAX, "implausible block size"

    recovered = b""
    while True:
        i = len(recovered)
        pad = block_size - 1 - (i % block_size)
        block_idx = i // block_size
        prefix = b"A" * pad

        target_ct = queries.get(fp(prefix))
        if target_ct is None:
            break  # no more aligned queries: secret fully recovered
        target = block(target_ct, block_idx, block_size)

        found = None
        for c in range(0x20, 0x7F):
            guess_ct = queries.get(fp(prefix + recovered + bytes([c])))
            if guess_ct is None:
                continue
            if block(guess_ct, block_idx, block_size) == target:
                found = c
                break
        if found is None:
            break  # reached padding past the end of the secret
        recovered += bytes([found])

    flag = recovered.decode()
    print(f"[+] block size = {block_size}")
    print(f"[+] recovered {len(recovered)} bytes")
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "oracle_log.json"
    )
    solve(sys.argv[1] if len(sys.argv) > 1 else default)
