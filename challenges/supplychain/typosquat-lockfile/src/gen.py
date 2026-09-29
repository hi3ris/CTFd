#!/usr/bin/env python3
"""Generate the typosquat-lockfile artifact bundle.

A `package-lock.json` resolves a set of dependencies. Every legitimate one is
served from `registry.npmjs.org`; exactly one look-alike name (`expres`, a
typosquat of `express`) is resolved from an attacker-controlled mirror. That
squatted package's tarball hides the flag (ROT13 of a base64 string).
"""

import base64
import codecs
import gzip
import hashlib
import io
import json
import os
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

FLAG = "NCTF{typ0squ4t_expres_not_express_7c2e}"

GOOD = "https://registry.npmjs.org"
EVIL = "https://npm-registry-mirror.dev"


def make_tarball(path, files):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo("package/" + name)
            info.size = len(data)
            info.mtime = 0
            tar.addfile(info, io.BytesIO(data))
    body = gzip.compress(raw.getvalue(), mtime=0)
    with open(path, "wb") as fh:
        fh.write(body)
    return "sha512-" + base64.b64encode(hashlib.sha512(body).digest()).decode()


def build():
    packages = {
        "express": "4.18.2",
        "lodash": "4.17.21",
        "chalk": "5.3.0",
        "expres": "4.18.9",  # the typosquat
        "debug": "4.3.4",
    }

    lock = {
        "name": "acme-frontend",
        "version": "1.0.0",
        "lockfileVersion": 3,
        "packages": {},
    }

    for name, version in packages.items():
        if name == "expres":
            # Malicious payload: base64 of the flag, then ROT13 to obscure it.
            hidden = codecs.encode(base64.b64encode(FLAG.encode()).decode(), "rot_13")
            index = (
                b"// telemetry helper\nvar _p = '"
                + hidden.encode()
                + b"';\nmodule.exports = require('http');\n"
            )
            host = EVIL
        else:
            index = b"module.exports = {};\n"
            host = GOOD
        pkg_json = json.dumps({"name": name, "version": version}).encode()
        tgz = f"{name}-{version}.tgz"
        integrity = make_tarball(
            os.path.join(OUT, tgz),
            {"package.json": pkg_json, "index.js": index},
        )
        lock["packages"]["node_modules/" + name] = {
            "version": version,
            "resolved": f"{host}/{name}/-/{tgz}",
            "integrity": integrity,
        }

    with open(os.path.join(OUT, "package-lock.json"), "w") as fh:
        json.dump(lock, fh, indent=2)
        fh.write("\n")

    print("built typosquat-lockfile artifacts")


if __name__ == "__main__":
    build()
