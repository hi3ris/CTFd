"""Greeting-card renderer -- source handout.

The card message is built by concatenating the user-supplied `name` directly
into the template SOURCE, then rendering it (server-side template injection).
The render environment exposes a `config` global -- a leakable, framework-style
config object. The flag is shipped sealed and can only be unsealed with a key
derived from the *rendered output* of the intended `{{ config }}` leak, so the
SSTI must actually be evaluated; there is no constant vault key to call.

Input contract:
    POST /card  {"name": "<text>"}
    -> renders  env.from_string("Dear " + name + ", welcome to Lome!")
"""

import hashlib

from flask import Flask, jsonify, request
from jinja2 import Environment

app = Flask(__name__)

# Flag sealed as: flag XOR keystream(sha256(<rendered leak>)).  The key material
# is NOT a constant here -- it is the exact string the intended SSTI payload
# ({{ config }}) renders to.  Unsealing therefore requires evaluating the SSTI.
_SEALED = bytes.fromhex(
    "f95fe0a32347cdcab478687f0c0580b1ffe269a29dd5a47e1404c61d"
    "1c1cadcc4f1b35f6208b1068dd414821c2bcf3"
)


class AppConfig:
    """A leakable framework-style config object exposed to the template."""

    DEBUG = False
    KIOSK = "lome-greeting-kiosk"
    SIGNING_SALT = "tg-kiosk-9f2c1a7d"

    def __repr__(self) -> str:
        return "Config(DEBUG=%r, KIOSK=%r, SIGNING_SALT=%r)" % (
            self.DEBUG,
            self.KIOSK,
            self.SIGNING_SALT,
        )


def _keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


env = Environment()
env.globals["config"] = AppConfig()


def render_card(name: str) -> str:
    # Vulnerable: user input concatenated into the template source (SSTI).
    template = env.from_string("Dear " + name + ", welcome to Lome!")
    return template.render()


def unseal(rendered_leak: str) -> str:
    """Unseal the flag using the rendered SSTI leak as the key.

    Only the card produced by the intended `{{ config }}` payload yields the
    correct key; any other rendering (e.g. a plain name) derives a wrong key.
    """
    key = hashlib.sha256(rendered_leak.encode()).digest()
    ks = _keystream(key, len(_SEALED))
    return bytes(a ^ b for a, b in zip(_SEALED, ks)).decode()


@app.post("/card")
def card():
    name = request.get_json(force=True).get("name", "")
    return jsonify(card=render_card(name))


if __name__ == "__main__":
    app.run(port=8080)
