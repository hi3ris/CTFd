#!/usr/bin/env python3
"""Offline solver: loads shipped artifacts and prints the flag."""

import json
import os


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


N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def inv(a, m):
    return pow(a, m - 2, m)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    art = json.load(open(os.path.join(here, "..", "signatures.json")))
    r = int(art["r"], 16)
    s1 = int(art["s1"], 16)
    s2 = int(art["s2"], 16)
    z1 = int.from_bytes(keccak256(art["message1"].encode()), "big") % N
    z2 = int.from_bytes(keccak256(art["message2"].encode()), "big") % N
    # same r => same nonce k reused: recover k then the private key d
    k = (z1 - z2) * inv((s1 - s2) % N, N) % N
    d = (s1 * k - z1) * inv(r, N) % N
    cipher = bytes.fromhex(art["cipher_hex"])
    ks = keystream(d.to_bytes(32, "big"), len(cipher))
    print(bytes(a ^ b for a, b in zip(cipher, ks)).decode())


if __name__ == "__main__":
    main()
