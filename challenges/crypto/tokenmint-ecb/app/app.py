#!/usr/bin/env python3
"""Sealbox ECB — an AES-ECB token service vulnerable to cut-and-paste.

Design (served challenge, per-team flag):

  * ``/token?name=X`` returns an ECB-encrypted session token whose plaintext is
    ``name=<X>&role=user`` (PKCS#7-padded). AES-ECB encrypts each 16-byte block
    independently, so identical plaintext blocks give identical ciphertext blocks
    and blocks can be rearranged.
  * ``/flag?token=HEX`` decrypts the token and, if the parsed ``role`` is
    ``admin``, returns this instance's flag.

Because the caller controls ``name`` (raw bytes), they can (1) obtain a block
that decrypts to ``admin`` + PKCS#7 padding and (2) align the token so the final
block is exactly the ``role`` value, then splice the two — forging ``role=admin``
without the key.

The flag at ``/flag.txt`` is exposed by no route other than the admin check.
"""
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from flask import Flask, jsonify, request

app = Flask(__name__)

_KEY = os.urandom(16)
BS = 16


def pad(b: bytes) -> bytes:
    n = BS - (len(b) % BS)
    return b + bytes([n]) * n


def unpad(b: bytes) -> bytes:
    if not b or len(b) % BS:
        raise ValueError("bad length")
    n = b[-1]
    if n < 1 or n > BS or b[-n:] != bytes([n]) * n:
        raise ValueError("bad padding")
    return b[:-n]


def ecb_enc(pt: bytes) -> bytes:
    c = Cipher(algorithms.AES(_KEY), modes.ECB()).encryptor()
    return c.update(pt) + c.finalize()


def ecb_dec(ct: bytes) -> bytes:
    d = Cipher(algorithms.AES(_KEY), modes.ECB()).decryptor()
    return d.update(ct) + d.finalize()


@app.route("/")
def index():
    return jsonify(
        {
            "service": "tokenmint-ecb",
            "token": "/token?name=X  -> ECB('name=<X>&role=user')",
            "flag": "/flag?token=HEX  (needs role=admin)",
        }
    )


@app.route("/token")
def token():
    # name arrives percent-decoded; take raw bytes so padding bytes survive.
    name = request.args.get("name", "").encode("latin1")
    pt = pad(b"name=" + name + b"&role=user")
    return jsonify({"token": ecb_enc(pt).hex()})


def _parse(pt: bytes) -> dict:
    out = {}
    for part in pt.split(b"&"):
        if b"=" in part:
            k, _, v = part.partition(b"=")
            out[k.decode("latin1")] = v.decode("latin1")
    return out


@app.route("/flag")
def flag():
    try:
        pt = unpad(ecb_dec(bytes.fromhex(request.args.get("token", ""))))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if _parse(pt).get("role") != "admin":
        return jsonify({"error": "not admin"}), 403
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return jsonify({"flag": fh.read().strip()})
    except OSError:
        return jsonify({"error": "flag unavailable"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
