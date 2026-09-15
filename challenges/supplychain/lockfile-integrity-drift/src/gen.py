#!/usr/bin/env python3
"""Generate the lockfile-integrity-drift artifact bundle.

A `package-lock.json` pins an `integrity` (sha512) for every dependency. All
tarballs match their pin except one: the shipped tarball for that package was
swapped after the lockfile was written, so its real hash differs. The swapped
(malicious) tarball carries the flag.
"""

import base64
import gzip
import hashlib
import io
import json
import os
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

FLAG = "NCTF{1ntegrity_hash_mismatch_carries_flag_d3e1}"


def sri(body):
    return "sha512-" + base64.b64encode(hashlib.sha512(body).digest()).decode()


def make_tarball(files):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo("package/" + name)
            info.size = len(data)
            info.mtime = 0
            tar.addfile(info, io.BytesIO(data))
    return gzip.compress(raw.getvalue(), mtime=0)


def build():
    deps = {
        "left-pad": "1.3.0",
        "ansi-styles": "6.2.1",
        "semver": "7.5.4",
        "minimist": "1.2.8",
    }
    victim = "minimist"

    lock = {
        "name": "acme-cli",
        "version": "2.1.0",
        "lockfileVersion": 3,
        "packages": {},
    }

    for name, version in deps.items():
        # Original benign tarball -> its hash goes into the lockfile.
        benign = make_tarball(
            {
                "package.json": json.dumps({"name": name, "version": version}).encode(),
                "index.js": b"module.exports = {};\n",
            }
        )
        pinned_integrity = sri(benign)

        tgz = f"{name}-{version}.tgz"
        if name == victim:
            # Attacker swaps the shipped tarball; the lockfile still pins the
            # OLD hash, creating a detectable mismatch. This tarball holds
            # the flag.
            flag_b64 = base64.b64encode(FLAG.encode()).decode()
            evil = make_tarball(
                {
                    "package.json": json.dumps(
                        {"name": name, "version": version}
                    ).encode(),
                    "index.js": (
                        b"// build metadata\nvar _sig = '"
                        + flag_b64.encode()
                        + b"';\nmodule.exports = _sig;\n"
                    ),
                }
            )
            shipped = evil
        else:
            shipped = benign

        with open(os.path.join(OUT, tgz), "wb") as fh:
            fh.write(shipped)

        lock["packages"]["node_modules/" + name] = {
            "version": version,
            "resolved": f"https://registry.npmjs.org/{name}/-/{tgz}",
            "integrity": pinned_integrity,
        }

    with open(os.path.join(OUT, "package-lock.json"), "w") as fh:
        json.dump(lock, fh, indent=2)
        fh.write("\n")

    print("built lockfile-integrity-drift artifacts")


if __name__ == "__main__":
    build()
