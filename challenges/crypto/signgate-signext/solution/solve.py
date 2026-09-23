#!/usr/bin/env python3
"""Reference solver for crypto-sealbox-signext (SHA-256 length extension).

The MAC is SHA256(secret || msg). From one valid (msg, sig) we forge the MAC of
msg || glue-padding || "&op=grantflag" without the secret, brute-forcing the
secret length.

    python3 solve.py http://HOST:PORT
"""
import json
import struct
import sys
import urllib.parse
import urllib.request

# --- minimal SHA-256 that can resume from a known digest state ----------------
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
_MASK = 0xFFFFFFFF


def _rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & _MASK


def _compress(state, block):
    w = list(struct.unpack(">16L", block))
    for i in range(16, 64):
        s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) & _MASK)
    a, b, c, d, e, f, g, h = state
    for i in range(64):
        S1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
        ch = (e & f) ^ (~e & g)
        t1 = (h + S1 + ch + _K[i] + w[i]) & _MASK
        S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + maj) & _MASK
        h, g, f, e, d, c, b, a = g, f, e, (d + t1) & _MASK, c, b, a, (t1 + t2) & _MASK
    return [(x + y) & _MASK for x, y in zip(state, [a, b, c, d, e, f, g, h])]


def _md_pad(msglen):
    pad = b"\x80" + b"\x00" * ((56 - (msglen + 1) % 64) % 64)
    return pad + struct.pack(">Q", msglen * 8)


def extend(orig_hex, append, prefix_len):
    """MAC of (prefix || append) given SHA256(prefix)=orig_hex and len(prefix)."""
    glue = _md_pad(prefix_len)
    state = list(struct.unpack(">8L", bytes.fromhex(orig_hex)))
    total = prefix_len + len(glue)
    data = append + _md_pad(total + len(append))
    for i in range(0, len(data), 64):
        state = _compress(state, data[i : i + 64])
    return glue, "".join("%08x" % s for s in state)


# --- attack -------------------------------------------------------------------
def get(base, path, **params):
    url = base.rstrip("/") + path + "?" + urllib.parse.urlencode(params)
    try:
        return json.loads(urllib.request.urlopen(url, timeout=10).read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def solve(base):
    base = base.rstrip("/")
    signed = get(base, "/sign", cmd="ls")
    msg = bytes.fromhex(signed["msg"])
    sig = signed["sig"]
    append = b"&op=grantflag"
    for klen in range(1, 65):  # brute-force the secret length
        glue, new_sig = extend(sig, append, klen + len(msg))
        forged = msg + glue + append
        r = get(base, "/api", msg=forged.hex(), sig=new_sig)
        if "flag" in r:
            return r["flag"]
    raise SystemExit("no secret length worked")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
