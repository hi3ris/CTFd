"""Greeting-card renderer -- source handout.

The card message is built by concatenating the user-supplied `name` directly
into the template SOURCE, then rendering it. The render environment exposes a
`vault` object. The flag is never emitted by normal input.

Input contract:
    POST /card  {"name": "<text>"}
    -> renders  env.from_string("Dear " + name + ", welcome to Lome!")
"""

import hashlib

from flask import Flask, jsonify, request
from jinja2 import Environment

app = Flask(__name__)

_SEALED = bytes.fromhex(
    "69aabc856cf1a6a721291732cb06b53b1c4ed3186714edd4277f258a"
    "d5bf855af08fe044b70c498bcc6983ae55f575"
)
_VAULT_KEY = b"greeting-vault-2026"


def _keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


class Vault:
    def reveal(self) -> str:
        ks = _keystream(hashlib.sha256(_VAULT_KEY).digest(), len(_SEALED))
        return bytes(a ^ b for a, b in zip(_SEALED, ks)).decode()


env = Environment()
env.globals["vault"] = Vault()


def render_card(name: str) -> str:
    # Vulnerable: user input concatenated into the template source (SSTI).
    template = env.from_string("Dear " + name + ", welcome to Lome!")
    return template.render()


@app.post("/card")
def card():
    name = request.get_json(force=True).get("name", "")
    return jsonify(card=render_card(name))


if __name__ == "__main__":
    app.run(port=8080)
