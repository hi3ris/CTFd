#!/usr/bin/env python3
"""Producer for ssti-jinja sealed flag blob.

The flag is sealed with a key derived from the *rendered output* of the intended
SSTI payload ({{ config }}) against the shipped template, so the seal cannot be
opened without actually evaluating the injection.  This mirrors app.py exactly:
keep AppConfig / the template wrapper in sync between the two.
"""

import hashlib

from jinja2 import Environment

FLAG = "NCTF{jinja2_ssti_config_leak_via_render_string}"

# Must match app.py's intended payload.
PAYLOAD = "{{ config }}"


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


def keystream(key: bytes, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def main() -> None:
    env = Environment()
    env.globals["config"] = AppConfig()
    rendered = env.from_string("Dear " + PAYLOAD + ", welcome to Lome!").render()
    key = hashlib.sha256(rendered.encode()).digest()
    ct = bytes(a ^ b for a, b in zip(FLAG.encode(), keystream(key, len(FLAG))))
    print("rendered leak =", rendered)
    print("SEALED =", ct.hex())


if __name__ == "__main__":
    main()
