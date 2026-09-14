"""Profile service -- source handout (backed by users.json).

PATCH /api/me merges the request JSON straight into the stored user record with
no field allowlist. GET /api/me/flag returns the flag to admins. A captured
benign update (capture.http) is shipped, along with the user store.
"""

import hashlib
import json

from flask import Flask, jsonify, request

app = Flask(__name__)

ADMIN_SEAL_KEY = b"profile-svc-admin-seal-2026"
SEALED_FLAG_HEX = (
    "4c6e7c8fadd91f899ff01d83c464215efd80ce6c86f4f903cb0a1c8c"
    "081a3e85bbf4d8a95b5c4a1558e9c32b23fd4d"
)

CURRENT_USER_ID = 7


def load_user():
    store = json.load(open("users.json"))
    return next(u for u in store["users"] if u["id"] == CURRENT_USER_ID)


def _keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


@app.patch("/api/me")
def update_me():
    user = load_user()
    body = request.get_json(force=True)
    # Vulnerable: whole body merged in, including privileged fields.
    user.update(body)
    return jsonify(user)


@app.get("/api/me/flag")
def me_flag():
    user = load_user()
    if not user.get("is_admin"):
        return jsonify(error="admins only"), 403
    ct = bytes.fromhex(SEALED_FLAG_HEX)
    key = hashlib.sha256(ADMIN_SEAL_KEY).digest()
    ks = _keystream(key, len(ct))
    return jsonify(flag=bytes(a ^ b for a, b in zip(ct, ks)).decode())


if __name__ == "__main__":
    app.run(port=8080)
