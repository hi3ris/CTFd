"""Members Panel -- Flask app source handout.

The signing key is hardcoded here (and was also present in the deploy log,
settings.py). Sessions are the default Flask itsdangerous-signed cookies. The
admin panel unseals a flag; the public signup only ever grants role=guest.
"""

import hashlib

from flask import Flask, jsonify, session

app = Flask(__name__)
app.secret_key = "s3cr3t-flask-signing-key-do-not-share-8842"

SEALED_FLAG_HEX = (
    "89008e3e14104f5680c3a3019d2bc222ab35396e916d5f4afa7773cf"
    "e11a83de5604021d700030cad2576ea6d522e02c81d3"
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
    key = hashlib.sha256(app.secret_key.encode() + b"|panel-seal").digest()
    ks = _keystream(key, len(ct))
    return bytes(a ^ b for a, b in zip(ct, ks)).decode()


@app.get("/signup")
def signup():
    # Public users are always guests.
    session["uid"] = 7
    session["role"] = "guest"
    session["display"] = "guest"
    return jsonify(ok=True)


@app.get("/admin/flag")
def admin_flag():
    if session.get("role") != "admin":
        return jsonify(error="admins only"), 403
    return jsonify(flag=unseal_flag())


if __name__ == "__main__":
    app.run(port=5000)
