#!/usr/bin/env python3
"""Reference solver for 'imds-ssrf'.

Parse the SSRF proxy capture: the third upstream response is the IMDS role
credential document. Pull the SecretAccessKey out of it, derive the XOR
keystream SHA256(SecretAccessKey), and decrypt the operator note to read the
flag.
"""

import base64
import hashlib
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def read(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def solve() -> str:
    cap = read("ssrf-capture.log")
    secret = re.search(r'"SecretAccessKey"\s*:\s*"([^"]+)"', cap).group(1)
    akid = re.search(r'"AccessKeyId"\s*:\s*"([^"]+)"', cap).group(1)
    print(f"[*] IMDS role creds: AccessKeyId={akid}")
    print(f"[*] SecretAccessKey={secret}")

    note = read("notes.enc")
    b64 = [ln.strip() for ln in note.splitlines() if ln and not ln.startswith("#")][0]
    ct = base64.b64decode(b64)
    ks = keystream(hashlib.sha256(secret.encode()).digest(), len(ct))
    flag = bytes(a ^ b for a, b in zip(ct, ks)).decode()
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    solve()
