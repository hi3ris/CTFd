#!/usr/bin/env python3
"""Reference solver for 'twister-tell'.

MT19937's tempering step is fully invertible, so 624 consecutive 32-bit outputs
untemper into the generator's entire internal state. Rebuilding that state lets
us clone the PRNG and reproduce the *next* outputs -- the keystream used to
encrypt the flag.
"""
import os
import random
import sys


def undo_right(y: int, shift: int) -> int:
    res = y
    for _ in range(0, 32, shift):
        res = y ^ (res >> shift)
    return res & 0xFFFFFFFF


def undo_left(y: int, shift: int, mask: int) -> int:
    res = y
    for _ in range(0, 32, shift):
        res = y ^ ((res << shift) & mask)
    return res & 0xFFFFFFFF


def untemper(y: int) -> int:
    y = undo_right(y, 18)
    y = undo_left(y, 15, 0xEFC60000)
    y = undo_left(y, 7, 0x9D2C5680)
    y = undo_right(y, 11)
    return y


def solve(outputs_path: str, ct_path: str) -> str:
    with open(outputs_path, encoding="utf-8") as fh:
        leaked = [int(line) for line in fh if line.strip()]
    assert len(leaked) >= 624
    with open(ct_path, encoding="utf-8") as fh:
        ct = bytes.fromhex(fh.read().strip())

    state = tuple(untemper(x) for x in leaked[:624])
    rng = random.Random()
    rng.setstate((3, state + (624,), None))

    ks = bytearray()
    while len(ks) < len(ct):
        ks += rng.getrandbits(32).to_bytes(4, "big")
    flag = bytes(a ^ b for a, b in zip(ct, ks)).decode()
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    outs = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "outputs.txt")
    enc = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "..", "flag.enc")
    solve(outs, enc)
