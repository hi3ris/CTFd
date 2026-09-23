"""Tokenforge — a chain: crypto oracle → forged admin cookie → hidden deser.

Design (served challenge, per-team flag):

  Stage 1 (crypto): ``/login`` returns a cookie that is the ASCII string
    ``role=guest`` XORed with a fixed per-instance keystream (a stream cipher
    with a reused keystream). Known plaintext recovers the keystream, so a
    ``role=admin`` cookie can be forged (both strings are 10 bytes).
  Stage 2 (hidden endpoint): ``/console`` requires an admin cookie and then
    deserializes an ``obj`` into a registry class with no allow-list — the
    registry holds a ``FlagDumper`` gadget.

Reverse the XOR (recover the keystream from the guest cookie), forge the admin
cookie, then hit the admin-only console with the gadget. The flag at
``/flag.txt`` is served by no route.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

_KS = os.urandom(16)  # reused keystream (the crypto flaw)


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


def _xor(data):
    return bytes(b ^ _KS[i % len(_KS)] for i, b in enumerate(data))


class Note:
    def __init__(self, text="", **_):
        self.text = text

    def render(self):
        return f"note: {self.text}"


class FlagDumper:
    def __init__(self, **_):
        self.output = _flag()

    def render(self):
        return self.output


REGISTRY = {"Note": Note, "FlagDumper": FlagDumper}


def _role(cookie_hex):
    try:
        return _xor(bytes.fromhex(cookie_hex)).decode("latin-1")
    except ValueError:
        return ""


@app.route("/")
def index():
    return jsonify(
        {
            "service": "tokenforge",
            "login": "GET /login  -> guest cookie",
            "console": "POST /console {cookie, obj:{__class__}}  (admin only)",
        }
    )


@app.route("/login")
def login():
    cookie = _xor(b"role=guest").hex()
    return jsonify({"cookie": cookie, "note": "cookie = role string, stream-encrypted"})


@app.route("/console", methods=["POST"])
def console():
    b = request.get_json(silent=True) or {}
    if _role(b.get("cookie", "")) != "role=admin":
        return jsonify({"error": "admin cookie required"}), 403
    obj = b.get("obj") or {}
    cls = obj.get("__class__", "Note")
    if cls not in REGISTRY:
        return jsonify({"error": "unknown class", "registry": sorted(REGISTRY)}), 400
    kwargs = {k: v for k, v in obj.items() if k != "__class__"}
    return jsonify({"result": REGISTRY[cls](**kwargs).render()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
