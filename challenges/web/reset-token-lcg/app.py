"""Password reset service -- source handout.

Reset tokens are generated from a linear congruential generator seeded with the
UNIX timestamp (whole seconds) of the request. The reset log (reset_log.txt)
records the issue time of each token. The admin token was emailed, not logged.
"""

import datetime
import hashlib

from flask import Flask, jsonify, request

app = Flask(__name__)

A = 1664525
C = 1013904223
M = 2**32

SEALED_FLAG_HEX = (
    "dc2b5c1b90e511c962f8328d76603381d83a694a7aa4cf06653fb74c"
    "8136e0e643a1036858fa495fbbaf29646998"
)


def make_token(seed: int) -> str:
    state = seed % M
    parts = []
    for _ in range(4):
        state = (A * state + C) % M
        parts.append("%08x" % state)
    return "".join(parts)


def _keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


@app.post("/reset/request")
def reset_request():
    # A fresh token is seeded from the current time and emailed to the user.
    seed = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    return jsonify(ok=True, token=make_token(seed))


@app.get("/reset/confirm")
def reset_confirm():
    token = request.args.get("token", "")
    # Only the (predictable) admin reset token unseals the flag.
    key = hashlib.sha256(b"resetseal|" + token.encode()).digest()
    ct = bytes.fromhex(SEALED_FLAG_HEX)
    candidate = bytes(a ^ b for a, b in zip(ct, _keystream(key, len(ct))))
    try:
        text = candidate.decode()
    except UnicodeDecodeError:
        return jsonify(error="bad token"), 403
    if text.startswith("NCTF{"):
        return jsonify(flag=text)
    return jsonify(error="bad token"), 403


if __name__ == "__main__":
    app.run(port=8080)
