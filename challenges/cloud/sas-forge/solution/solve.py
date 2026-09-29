#!/usr/bin/env python3
"""Reference solver for 'sas-forge'.

With the leaked Azure Storage account key, forge a Service SAS for the private
blob without touching Azure. Reconstruct the exact StringToSign (field layout
for signedVersion 2020-12-06), HMAC-SHA256 it with the base64-decoded account
key, and base64 the result -> the SAS `sig`. The sealed blob's XOR keystream is
SHA256(that sig); decrypt for the flag.
"""

import base64
import hashlib
import hmac
import json
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
    account_key_b64 = re.search(
        r"account_key\s*=\s*(\S+)", read("leaked-account-key.txt")
    ).group(1)
    params = json.loads(read("sas-params.json"))
    q = params["sas_query_params"]

    account = params["account"]
    container = params["container"]
    blob = params["blob"]
    canon = f"/blob/{account}/{container}/{blob}"

    string_to_sign = "\n".join(
        [
            q["sp"],
            q["st"],
            q["se"],
            canon,
            q["si"],
            q["sip"],
            q["spr"],
            q["sv"],
            q["sr"],
            q["sst"],
            q["ses"],
            q["rscc"],
            q["rscd"],
            q["rsce"],
            q["rscl"],
            q["rsct"],
        ]
    )

    key = base64.b64decode(account_key_b64)
    sig = base64.b64encode(
        hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    ).decode()
    print("[*] canonicalizedResource =", canon)
    print("[*] forged SAS sig        =", sig)

    body = read("flag-blob.enc")
    b64 = [ln.strip() for ln in body.splitlines() if ln and not ln.startswith("#")][0]
    ct = base64.b64decode(b64)
    ks = keystream(hashlib.sha256(sig.encode()).digest(), len(ct))
    flag = bytes(a ^ b for a, b in zip(ct, ks)).decode()
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    solve()
