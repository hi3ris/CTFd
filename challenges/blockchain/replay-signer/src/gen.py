#!/usr/bin/env python3
"""Regenerate signatures.json for replay-signer (deterministic)."""

import json


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


P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
FLAG = "NCTF{same_nonce_leaks_the_whole_key}"


def inv(a, m):
    return pow(a, m - 2, m)


def padd(pt, q):
    if pt is None:
        return q
    if q is None:
        return pt
    if pt[0] == q[0] and (pt[1] + q[1]) % P == 0:
        return None
    if pt == q:
        lam = 3 * pt[0] * pt[0] * inv(2 * pt[1], P) % P
    else:
        lam = (q[1] - pt[1]) * inv(q[0] - pt[0], P) % P
    x = (lam * lam - pt[0] - q[0]) % P
    y = (lam * (pt[0] - x) - pt[1]) % P
    return (x, y)


def pmul(k, pt):
    r = None
    while k:
        if k & 1:
            r = padd(r, pt)
        pt = padd(pt, pt)
        k >>= 1
    return r


def main():
    d = 0xC0FFEE1234567890ABCDEF0011223344556677889900AABBCCDDEEFF01020304 % N
    k = 0xDEADBEEFCAFEBABE1122334455667788990011223344556677889900AABBCCDD % N
    m1, m2 = b"withdraw:100 to treasury", b"withdraw:250 to treasury"
    z1 = int.from_bytes(keccak256(m1), "big") % N
    z2 = int.from_bytes(keccak256(m2), "big") % N
    r = pmul(k, (GX, GY))[0] % N
    s1 = inv(k, N) * (z1 + r * d) % N
    s2 = inv(k, N) * (z2 + r * d) % N
    pub = pmul(d, (GX, GY))
    pb = pub[0].to_bytes(32, "big") + pub[1].to_bytes(32, "big")
    signer = "0x" + keccak256(pb).hex()[-40:]
    ks = keystream(d.to_bytes(32, "big"), len(FLAG))
    cipher = bytes(a ^ b for a, b in zip(FLAG.encode(), ks)).hex()
    art = {
        "note": "two signatures by the same signer; the vault key derives from the private key",
        "signer": signer,
        "message1": m1.decode(),
        "message2": m2.decode(),
        "r": hex(r),
        "s1": hex(s1),
        "s2": hex(s2),
        "cipher_hex": cipher,
    }
    with open("signatures.json", "w") as f:
        json.dump(art, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
