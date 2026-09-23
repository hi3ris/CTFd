#!/usr/bin/env python3
"""Reference solver for crypto-oracle-cascade.

Chain: the padding oracle at /whoami lets us decrypt an arbitrary AES block
(recover its intermediate state) without the key. With one block's intermediate
state we forge an IV so that IV||C decrypts to role=admin (CBC-R), then present
that cookie to /flag.

    python3 solve.py http://HOST:PORT
"""
import json
import os
import sys
import urllib.request

BS = 16
TARGET = b"role=admin"


def pad(data):
    n = BS - (len(data) % BS)
    return data + bytes([n]) * n


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def make_oracle(base):
    base = base.rstrip("/")

    def oracle(cookie_hex):
        url = base + "/whoami?cookie=" + cookie_hex
        try:
            urllib.request.urlopen(url, timeout=10)
            return True  # 200 -> valid padding
        except urllib.error.HTTPError as e:
            return e.code != 400  # 400 -> bad padding

    return oracle


def decrypt_block(oracle, cblock):
    """Recover the AES-decrypt intermediate state of a single block."""
    inter = bytearray(BS)
    for padv in range(1, BS + 1):
        prev = bytearray(BS)
        for k in range(1, padv):
            prev[BS - k] = inter[BS - k] ^ padv
        pos = BS - padv
        for guess in range(256):
            prev[pos] = guess
            if oracle((bytes(prev) + cblock).hex()):
                if padv == 1:
                    # guard against the \x02\x02 false positive: perturb prev[-2]
                    probe = bytearray(prev)
                    probe[BS - 2] ^= 0xFF
                    if not oracle((bytes(probe) + cblock).hex()):
                        continue
                inter[pos] = guess ^ padv
                break
        else:
            raise RuntimeError(f"no byte found at pad {padv}")
    return bytes(inter)


def solve(base):
    oracle = make_oracle(base)
    c1 = os.urandom(BS)  # arbitrary ciphertext block
    inter = decrypt_block(oracle, c1)
    iv = xor(inter, pad(TARGET))  # IV so that D(c1) ^ IV == padded target
    cookie = (iv + c1).hex()
    url = base.rstrip("/") + "/flag?cookie=" + cookie
    body = json.loads(urllib.request.urlopen(url, timeout=10).read().decode())
    return body["flag"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
