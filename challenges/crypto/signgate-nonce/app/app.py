#!/usr/bin/env python3
"""Nonce Climb — an ECDSA signing service that reuses its nonce.

Design (served challenge, per-team flag):

  * The service holds a secp256k1 key pair (per instance) and publishes the
    public key at ``/pubkey``.
  * ``/sign?msg=...`` signs arbitrary messages with ECDSA — but it **refuses any
    message containing ``admin``**. So you cannot simply ask it to sign the
    privileged command.
  * The bug: every signature uses the **same nonce ``k``**. With ECDSA, two
    signatures sharing a nonce share ``r`` and leak the private key.
  * ``/flag`` takes a message and an ECDSA signature; if the signature is valid
    for the published key *and* the message is the admin command, it returns
    this instance's flag.

Intended path: ask ``/sign`` for two different (non-admin) messages, notice the
shared ``r``, recover ``k`` then the private key ``d``, sign the admin command
yourself, and present it to ``/flag``.

The flag at ``/flag.txt`` is returned by no route other than this signature
check — there is no path that leaks it without a forged admin signature.
"""
import hashlib
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# secp256k1 domain parameters.
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (GX, GY)

ADMIN_COMMAND = "role=admin;grant=flag"


def inv(x, m):
    return pow(x, -1, m)


def ec_add(pt1, pt2):
    if pt1 is None:
        return pt2
    if pt2 is None:
        return pt1
    x1, y1 = pt1
    x2, y2 = pt2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if pt1 == pt2:
        m = (3 * x1 * x1) * inv(2 * y1, P) % P
    else:
        m = (y2 - y1) * inv((x2 - x1) % P, P) % P
    x3 = (m * m - x1 - x2) % P
    y3 = (m * (x1 - x3) - y1) % P
    return (x3, y3)


def ec_mul(k, pt):
    result = None
    addend = pt
    while k:
        if k & 1:
            result = ec_add(result, addend)
        addend = ec_add(addend, addend)
        k >>= 1
    return result


def _rand_scalar():
    return (int.from_bytes(os.urandom(32), "big") % (N - 1)) + 1


# Per-instance private key, and the reused nonce (the flaw).
_D = _rand_scalar()
_Q = ec_mul(_D, G)
_K = _rand_scalar()  # never regenerated: every signature reuses this nonce


def _z(msg: str) -> int:
    return int.from_bytes(hashlib.sha256(msg.encode()).digest(), "big") % N


def sign(msg: str):
    z = _z(msg)
    r = ec_mul(_K, G)[0] % N
    s = (inv(_K, N) * (z + r * _D)) % N
    return r, s


def verify(msg: str, r: int, s: int) -> bool:
    if not (1 <= r < N and 1 <= s < N):
        return False
    z = _z(msg)
    w = inv(s, N)
    u1 = (z * w) % N
    u2 = (r * w) % N
    pt = ec_add(ec_mul(u1, G), ec_mul(u2, _Q))
    if pt is None:
        return False
    return pt[0] % N == r


@app.route("/")
def index():
    return jsonify(
        {
            "service": "signgate-nonce",
            "pubkey": "/pubkey",
            "sign": "/sign?msg=...  (refuses messages containing 'admin')",
            "flag": "/flag?msg=...&r=...&s=...",
            "admin_command": ADMIN_COMMAND,
        }
    )


@app.route("/pubkey")
def pubkey():
    return jsonify({"curve": "secp256k1", "Qx": hex(_Q[0]), "Qy": hex(_Q[1])})


@app.route("/sign")
def sign_route():
    msg = request.args.get("msg", "")
    if not msg:
        return jsonify({"error": "msg required"}), 400
    if "admin" in msg:
        return jsonify({"error": "refused: privileged message"}), 403
    r, s = sign(msg)
    return jsonify({"msg": msg, "r": hex(r), "s": hex(s)})


@app.route("/flag")
def flag():
    msg = request.args.get("msg", "")
    try:
        r = int(request.args.get("r", ""), 16)
        s = int(request.args.get("s", ""), 16)
    except ValueError:
        return jsonify({"error": "r and s must be hex"}), 400
    if not verify(msg, r, s):
        return jsonify({"error": "bad signature"}), 401
    if msg != ADMIN_COMMAND:
        return jsonify({"error": "signature valid, but not the admin command"}), 403
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return jsonify({"flag": fh.read().strip()})
    except OSError:
        return jsonify({"error": "flag unavailable"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
