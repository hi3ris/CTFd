#!/usr/bin/env python3
"""Reference solver for crypto-kdf-slip.

The server key is SHA256('nctf-kdf-' + 4-digit seed) — only 10 000 keys. Grab the
guest token, brute-force the seed to recover the key, forge the admin token, open
/panel.

    python3 solve.py http://HOST:PORT
"""
import hashlib
import hmac
import json
import sys
import urllib.request


def get(url):
    return json.loads(urllib.request.urlopen(url, timeout=10).read().decode())


def solve(base):
    base = base.rstrip("/")
    guest = get(base + "/login")["token"]
    for seed in range(10000):
        k = hashlib.sha256(b"nctf-kdf-" + f"{seed:04d}".encode()).digest()
        if hmac.compare_digest(
            hmac.new(k, b"guest", hashlib.sha256).hexdigest(), guest
        ):
            admin = hmac.new(k, b"admin", hashlib.sha256).hexdigest()
            return get(base + "/panel?user=admin&token=" + admin)["flag"]
    raise SystemExit("seed not found")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
