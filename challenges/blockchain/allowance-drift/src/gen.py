#!/usr/bin/env python3
"""Regenerate token_state.json for allowance-drift (deterministic)."""

import json
import math


def keccak256(msg: bytes) -> bytes:
    rc = [
        0x0000000000000001,
        0x0000000000008082,
        0x800000000000808A,
        0x8000000080008000,
        0x000000000000808B,
        0x0000000080000001,
        0x8000000080008081,
        0x8000000000008009,
        0x000000000000008A,
        0x0000000000000088,
        0x0000000080008009,
        0x000000008000000A,
        0x000000008000808B,
        0x800000000000008B,
        0x8000000000008089,
        0x8000000000008003,
        0x8000000000008002,
        0x8000000000000080,
        0x000000000000800A,
        0x800000008000000A,
        0x8000000080008081,
        0x8000000000008080,
        0x0000000080000001,
        0x8000000080008008,
    ]
    rot = [
        [0, 36, 3, 41, 18],
        [1, 44, 10, 45, 2],
        [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39, 8, 14],
    ]
    mask = (1 << 64) - 1
    rate = 136

    def rol(x, n):
        return ((x << n) | (x >> (64 - n))) & mask

    st = [[0] * 5 for _ in range(5)]
    m = bytearray(msg)
    m.append(0x01)
    while len(m) % rate != 0:
        m.append(0x00)
    m[-1] ^= 0x80

    for off in range(0, len(m), rate):
        block = m[off : off + rate]
        for i in range(rate // 8):
            st[i % 5][i // 5] ^= int.from_bytes(block[i * 8 : i * 8 + 8], "little")
        for rnd in range(24):
            c = [st[x][0] ^ st[x][1] ^ st[x][2] ^ st[x][3] ^ st[x][4] for x in range(5)]
            d = [c[(x - 1) % 5] ^ rol(c[(x + 1) % 5], 1) for x in range(5)]
            for x in range(5):
                for y in range(5):
                    st[x][y] ^= d[x]
            b = [[0] * 5 for _ in range(5)]
            for x in range(5):
                for y in range(5):
                    b[y][(2 * x + 3 * y) % 5] = rol(st[x][y], rot[x][y])
            for x in range(5):
                for y in range(5):
                    st[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y])
            st[0][0] ^= rc[rnd]
    out = bytearray()
    for i in range(rate // 8):
        if len(out) >= 32:
            break
        out += (st[i % 5][i // 5]).to_bytes(8, "little")
    return bytes(out[:32])


def keystream(seed: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += keccak256(seed + counter.to_bytes(4, "big"))
        counter += 1
    return bytes(out[:length])


FLAG = "NCTF{allowance_never_decremented}"
VICTIM_BALANCE = 1000000
ALLOWANCE = 3000


def main():
    num_calls = math.ceil(VICTIM_BALANCE / ALLOWANCE)
    ks = keystream(num_calls.to_bytes(32, "big"), len(FLAG))
    cipher = bytes(a ^ b for a, b in zip(FLAG.encode(), ks)).hex()
    art = {
        "note": "victim state; compute how many transferFrom calls fully drain them",
        "victim_balance": VICTIM_BALANCE,
        "your_allowance": ALLOWANCE,
        "cipher_hex": cipher,
    }
    with open("token_state.json", "w") as f:
        json.dump(art, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
