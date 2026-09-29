"""Ops Console -- token-gated flag endpoint (source handout).

This is the exact server source that was running in production. The signing
key below was leaked in a committed `.env` (see config.env). Only an *admin*
token unseals the operations flag; the public login only ever mints `guest`.
"""

import hashlib

import jwt
from flask import Flask, jsonify, request

app = Flask(__name__)

# Leaked in a committed .env file (see config.env).
JWT_SECRET = "c0nsole-rot4tion-signing-key-2026"

# The operations flag is never stored in plaintext. It is sealed with a
# keystream derived from the signing key and only revealed to admin callers.
SEALED_FLAG_HEX = (
    "ad13d8e88f418fea96615aa96b1396d1a1277d5564d68dc263f23aca"
    "9a7e80a1a43b0af3378389b0539a210931da8a460496"
)


def _keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def unseal_flag() -> str:
    ct = bytes.fromhex(SEALED_FLAG_HEX)
    key = hashlib.sha256(JWT_SECRET.encode() + b"|ops-seal").digest()
    ks = _keystream(key, len(ct))
    return bytes(a ^ b for a, b in zip(ct, ks)).decode()


@app.post("/api/login")
def login():
    # Public accounts only ever receive the guest role.
    data = request.get_json(force=True)
    if (data.get("user"), data.get("pass")) != ("guest", "guest"):
        return jsonify(error="bad credentials"), 401
    token = jwt.encode({"sub": "guest", "role": "guest"}, JWT_SECRET, algorithm="HS256")
    return jsonify(token=token)


@app.get("/api/flag")
def flag():
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return jsonify(error="invalid token"), 401
    if claims.get("role") != "admin":
        return jsonify(error="admin only"), 403
    return jsonify(flag=unseal_flag())


if __name__ == "__main__":
    app.run(port=8080)
