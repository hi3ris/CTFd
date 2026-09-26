"""Profile service -- source handout (backed by users.json).

PATCH /api/me merges the request JSON straight into the stored user record with
no field allowlist. GET /api/me/flag returns the flag to admins. A captured
benign update (capture.http) is shipped, along with the user store.

The flag is sealed with a key derived from the *privileged* mass-assignment
body itself -- the canonical JSON of the exact fields that make an admin. Only
crafting that request (both `is_admin: true` and `role: "admin"`) yields the
key; there is no standalone constant seal key.
"""

import hashlib
import json

from flask import Flask, jsonify, request

app = Flask(__name__)

# flag XOR keystream(sha256(canonical privileged assignment)), where the
# canonical assignment is json.dumps({"is_admin": true, "role": "admin"},
# sort_keys=True, separators=(",", ":")).  The key lives nowhere as a constant.
SEALED_FLAG_HEX = (
    "24ff70ea1563ed56edb2627858375155823e988ec41095290d47ffe5"
    "58a0a6f95b13638d0f9ad89d770d0bba280adb"
)

# Fields that define an admin; their values on the record form the seal key.
ADMIN_ASSIGNMENT = ("is_admin", "role")

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
    if not (user.get("is_admin") is True and user.get("role") == "admin"):
        return jsonify(error="admins only"), 403
    # Derive the seal key from the privileged assignment now on the record.
    assignment = {k: user[k] for k in ADMIN_ASSIGNMENT}
    canonical = json.dumps(assignment, sort_keys=True, separators=(",", ":"))
    key = hashlib.sha256(canonical.encode()).digest()
    ct = bytes.fromhex(SEALED_FLAG_HEX)
    ks = _keystream(key, len(ct))
    return jsonify(flag=bytes(a ^ b for a, b in zip(ct, ks)).decode())


if __name__ == "__main__":
    app.run(port=8080)
