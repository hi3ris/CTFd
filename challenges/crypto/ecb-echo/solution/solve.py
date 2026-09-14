#!/usr/bin/env python3
"""Reference solver for 'ecb-echo'.

The captured service encrypts AES-ECB(attacker_input || SECRET). ECB is
deterministic and encrypts each 16-byte block independently, so by aligning the
unknown secret byte as the last byte of a block and comparing against every
possible last byte, we recover the secret one byte at a time.

The log already contains, per position, the aligned target block and a candidate
block for each printable guess, so recovery is a lookup: the guess whose
candidate block equals the target block is the secret byte.
"""
import json
import os
import sys


def solve(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        log = json.load(fh)

    # Confirm block size from the probe: length jumps by one block size.
    lens = [len(h) // 2 for h in log["probe"]]
    block_size = next(
        lens[k + 1] - lens[k] for k in range(len(lens) - 1) if lens[k + 1] != lens[k]
    )
    assert block_size == 16

    recovered = []
    for step in log["steps"]:
        target = step["target"]
        found = None
        for ch, cand in step["candidates"].items():
            if cand == target:
                found = ch
                break
        if found is None:
            raise SystemExit(f"no candidate matched at byte {len(recovered)}")
        recovered.append(found)

    flag = "".join(recovered)
    print(f"[+] block size = {block_size}")
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "oracle_log.json"
    )
    solve(sys.argv[1] if len(sys.argv) > 1 else default)
