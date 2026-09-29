#!/usr/bin/env python3
"""Reference solver for 'state-secret'.

Terraform stores every attribute in ``terraform.tfstate`` in plaintext, so the
vault passphrase (``random_password.vault.result``) is right there. We collect
all string values from the state file as candidate passphrases, then decrypt the
shipped ``vault.enc`` blob with each until one yields a ``NCTF{`` plaintext.

Blob format: ``b"ENC1" + salt(16) + iters(4, big-endian) + ciphertext``, with
``key = PBKDF2-HMAC-SHA256(passphrase, salt, iters)`` and a
``SHA256(key || counter)`` keystream. Pure standard library.
"""

import hashlib
import json
import os

MAGIC = b"ENC1"


def keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(8, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def collect_strings(obj, acc):
    if isinstance(obj, dict):
        for v in obj.values():
            collect_strings(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            collect_strings(v, acc)
    elif isinstance(obj, str):
        acc.append(obj)


def decrypt(blob: bytes, passphrase: str):
    if blob[:4] != MAGIC:
        return None
    salt = blob[4:20]
    iters = int.from_bytes(blob[20:24], "big")
    ct = blob[24:]
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, iters)
    pt = bytes(a ^ b for a, b in zip(ct, keystream(key, len(ct))))
    try:
        return pt.decode()
    except UnicodeDecodeError:
        return None


def solve(root: str) -> str:
    with open(os.path.join(root, "terraform.tfstate"), encoding="utf-8") as fh:
        state = json.load(fh)
    with open(os.path.join(root, "vault.enc"), "rb") as fh:
        blob = fh.read()

    candidates = []
    collect_strings(state, candidates)
    for cand in candidates:
        pt = decrypt(blob, cand)
        if pt and pt.startswith("NCTF{"):
            print("[+] passphrase from tfstate:", cand)
            print("[+] FLAG =", pt)
            return pt
    raise SystemExit("no candidate passphrase decrypted the blob")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
