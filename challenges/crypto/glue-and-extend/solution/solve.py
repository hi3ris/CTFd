#!/usr/bin/env python3
"""Reference solver for 'glue-and-extend'.

SHA-256 is a Merkle-Damgard hash: its output is just its internal chaining state
after processing message || padding. Given tag1 = SHA256(secret || command1) we
can load that state and *continue* hashing an appended suffix, obtaining
SHA256(secret || command1 || glue || suffix) without knowing the secret -- as
long as we know the total length that was hashed, which fixes the glue padding.

The secret length is unknown but small, so we brute-force it (1..64), forge the
elevated tag, derive the sealing key, and stop when the decrypted payload is the
flag.
"""
import hashlib
import os
import sys

_K = [
    0x428A2F98,
    0x71374491,
    0xB5C0FBCF,
    0xE9B5DBA5,
    0x3956C25B,
    0x59F111F1,
    0x923F82A4,
    0xAB1C5ED5,
    0xD807AA98,
    0x12835B01,
    0x243185BE,
    0x550C7DC3,
    0x72BE5D74,
    0x80DEB1FE,
    0x9BDC06A7,
    0xC19BF174,
    0xE49B69C1,
    0xEFBE4786,
    0x0FC19DC6,
    0x240CA1CC,
    0x2DE92C6F,
    0x4A7484AA,
    0x5CB0A9DC,
    0x76F988DA,
    0x983E5152,
    0xA831C66D,
    0xB00327C8,
    0xBF597FC7,
    0xC6E00BF3,
    0xD5A79147,
    0x06CA6351,
    0x14292967,
    0x27B70A85,
    0x2E1B2138,
    0x4D2C6DFC,
    0x53380D13,
    0x650A7354,
    0x766A0ABB,
    0x81C2C92E,
    0x92722C85,
    0xA2BFE8A1,
    0xA81A664B,
    0xC24B8B70,
    0xC76C51A3,
    0xD192E819,
    0xD6990624,
    0xF40E3585,
    0x106AA070,
    0x19A4C116,
    0x1E376C08,
    0x2748774C,
    0x34B0BCB5,
    0x391C0CB3,
    0x4ED8AA4A,
    0x5B9CCA4F,
    0x682E6FF3,
    0x748F82EE,
    0x78A5636F,
    0x84C87814,
    0x8CC70208,
    0x90BEFFFA,
    0xA4506CEB,
    0xBEF9A3F7,
    0xC67178F2,
]

MASK = 0xFFFFFFFF


def _rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & MASK


def _compress(h, block):
    w = [int.from_bytes(block[i * 4 : i * 4 + 4], "big") for i in range(16)]
    for i in range(16, 64):
        s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) & MASK)
    a, b, c, d, e, f, g, hh = h
    for i in range(64):
        s1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
        ch = (e & f) ^ (~e & g)
        t1 = (hh + s1 + ch + _K[i] + w[i]) & MASK
        s0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (s0 + maj) & MASK
        hh, g, f, e, d, c, b, a = g, f, e, (d + t1) & MASK, c, b, a, (t1 + t2) & MASK
    return [(x + y) & MASK for x, y in zip(h, [a, b, c, d, e, f, g, hh])]


def md_padding(msg_len: int) -> bytes:
    pad = b"\x80"
    pad += b"\x00" * ((56 - (msg_len + 1) % 64) % 64)
    pad += (msg_len * 8).to_bytes(8, "big")
    return pad


def sha256_extend(tag: bytes, processed_len: int, suffix: bytes) -> bytes:
    """Continue SHA-256 from `tag` (state after `processed_len` bytes) over
    `suffix`, returning SHA256(<processed_len bytes> || suffix)."""
    h = [int.from_bytes(tag[i * 4 : i * 4 + 4], "big") for i in range(8)]
    total = processed_len + len(suffix)
    data = suffix + md_padding(total)
    for i in range(0, len(data), 64):
        h = _compress(h, data[i : i + 64])
    return b"".join(x.to_bytes(4, "big") for x in h)


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def solve(path: str) -> str:
    fields = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                fields[k] = v
    command1 = fields["COMMAND"].encode()
    tag1 = bytes.fromhex(fields["TAG"])
    suffix = fields["SUFFIX"].encode()
    sealed = bytes.fromhex(fields["SEALED"])

    for secret_len in range(1, 65):
        glue = md_padding(secret_len + len(command1))
        processed = secret_len + len(command1) + len(glue)
        forged = sha256_extend(tag1, processed, suffix)
        pt = bytes(a ^ b for a, b in zip(sealed, keystream(forged, len(sealed))))
        if pt.startswith(b"NCTF{") and pt.endswith(b"}"):
            # Any assumed length whose glue lands in the same final block yields
            # the same total bit-length, hence the same forged tag; the smallest
            # such length is reported here.
            print(f"[+] forged elevated tag (assumed prefix length {secret_len})")
            print("[+] FLAG =", pt.decode())
            return pt.decode()
    raise SystemExit("no secret length recovered the flag")


if __name__ == "__main__":
    default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "token.txt"
    )
    solve(sys.argv[1] if len(sys.argv) > 1 else default)
