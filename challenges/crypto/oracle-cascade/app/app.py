#!/usr/bin/env python3
"""Oracle Cascade — an AES-CBC service with a padding oracle.

Design (served challenge, per-team flag):

  * ``/login`` issues an encrypted session cookie: ``IV || AES-CBC(key, token)``
    (hex), where ``token`` is ``role=user`` PKCS#7-padded. The key is per
    instance and never leaves the process.
  * ``/whoami?cookie=...`` decrypts the cookie and **distinguishes a padding
    error (400) from a valid decrypt (200)** — the padding oracle.
  * ``/flag?cookie=...`` decrypts, and if the padding is valid *and* the plaintext
    is exactly ``role=admin`` it returns this instance's flag.

Intended path: use the padding oracle (CBC-R) to forge a cookie that decrypts to
``role=admin`` without ever knowing the key, then present it to ``/flag``.

The flag at ``/flag.txt`` is returned by no route other than this admin check.
"""
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from flask import Flask, jsonify, request

app = Flask(__name__)

_KEY = os.urandom(16)
BS = 16
USER_TOKEN = b"role=user"
ADMIN_TOKEN = b"role=admin"


def pad(data: bytes) -> bytes:
    n = BS - (len(data) % BS)
    return data + bytes([n]) * n


def unpad(data: bytes) -> bytes:
    if not data or len(data) % BS != 0:
        raise ValueError("bad length")
    n = data[-1]
    if n < 1 or n > BS or data[-n:] != bytes([n]) * n:
        raise ValueError("bad padding")
    return data[:-n]


def _enc(iv: bytes, pt: bytes) -> bytes:
    c = Cipher(algorithms.AES(_KEY), modes.CBC(iv)).encryptor()
    return c.update(pt) + c.finalize()


def _dec(iv: bytes, ct: bytes) -> bytes:
    d = Cipher(algorithms.AES(_KEY), modes.CBC(iv)).decryptor()
    return d.update(ct) + d.finalize()


def decrypt_cookie(cookie_hex: str) -> bytes:
    raw = bytes.fromhex(cookie_hex)
    if len(raw) < 2 * BS or len(raw) % BS != 0:
        raise ValueError("bad length")
    iv, ct = raw[:BS], raw[BS:]
    return unpad(_dec(iv, ct))


@app.route("/")
def index():
    return jsonify(
        {
            "service": "oracle-cascade",
            "login": "/login -> cookie",
            "whoami": "/whoami?cookie=HEX  (200 valid padding / 400 bad padding)",
            "flag": "/flag?cookie=HEX  (needs role=admin)",
        }
    )


@app.route("/login")
def login():
    iv = os.urandom(BS)
    ct = _enc(iv, pad(USER_TOKEN))
    return jsonify({"cookie": (iv + ct).hex(), "role": "user"})


@app.route("/whoami")
def whoami():
    try:
        pt = decrypt_cookie(request.args.get("cookie", ""))
    except ValueError as e:
        # The oracle: padding failures are observable and distinct.
        return jsonify({"error": str(e)}), 400
    return jsonify({"role": pt.decode("latin1")})


@app.route("/flag")
def flag():
    try:
        pt = decrypt_cookie(request.args.get("cookie", ""))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if pt != ADMIN_TOKEN:
        return jsonify({"error": "not admin", "role": pt.decode("latin1")}), 403
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return jsonify({"flag": fh.read().strip()})
    except OSError:
        return jsonify({"error": "flag unavailable"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
