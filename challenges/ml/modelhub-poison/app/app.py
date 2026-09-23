#!/usr/bin/env python3
"""Modelhub Poison -- SERVED CHALLENGE STUB.

NON-FUNCTIONAL: this is a scaffold. Replace the placeholder below with the real
vulnerable service. The flag lives in /flag.txt (written by entrypoint.sh from
get_flag()); it must be reachable ONLY through the intended vulnerability, never
served by a route.

Build contract (see deploy/challenge-chains-blueprint.md):
  * success oracle is server-side -- the flag appears only after a real effect;
  * for a multi-stage chain, stage N's unlock is emitted only as an effect of
    stage N-1 (audit line, minted credential, revealed endpoint);
  * self-contained read channel (no attacker callback server).
"""
import os

from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return (
        "<h1>Modelhub Poison</h1><p>Scaffold stub. TODO: implement the vulnerability "
        "for challenge <code>ml-modelhub-poison</code>.</p>"
    )


# TODO: the vulnerable route(s) go here. The flag is /flag.txt, readable only via
# the intended exploit. Do not add a route that serves it directly.


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
