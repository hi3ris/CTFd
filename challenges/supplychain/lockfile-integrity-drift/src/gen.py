#!/usr/bin/env python3
"""Generate the lockfile-integrity-drift artifact bundle.

A `package-lock.json` pins an `integrity` (sha512) for every dependency. Every
shipped tarball matches its pin except one: the shipped tarball for that package
was tampered after the lockfile was written, so its real hash differs.

Crucially, the flag is *not* stored anywhere in plaintext or base64. The tamper
is a block of bytes appended *after* the gzip member of the victim tarball. Those
trailing bytes are the only reason the file's sha512 no longer matches the pin --
the mismatch delta and the payload are the same bytes. The trailing block is the
flag XORed with a keystream derived from that dependency's *pinned* integrity, so
recovery forces the player to (1) find which dep's sha512 drifted, (2) read the
delta that caused the drift, and (3) key off that dep's pinned integrity. Reading
the gzip member normally (npm/tar/zgrep) never sees the payload at all.
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

FLAG = b"NCTF{1ntegrity_hash_mismatch_carries_flag_d3e1}"


def sri(body):
    return "sha512-" + base64.b64encode(hashlib.sha512(body).digest()).decode()


def keystream(seed: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha512(seed + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def seal(payload: bytes, pinned_integrity: str) -> bytes:
    ks = keystream(pinned_integrity.encode(), len(payload))
    return bytes(a ^ b for a, b in zip(payload, ks))


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
        # Original benign tarball -> its hash is what the lockfile pins.
        benign = make_tarball(
            {
                "package.json": json.dumps({"name": name, "version": version}).encode(),
                "index.js": b"module.exports = {};\n",
            }
        )
        pinned_integrity = sri(benign)

        tgz = f"{name}-{version}.tgz"
        if name == victim:
            # Tamper: append a sealed block AFTER the gzip member. The gzip
            # payload is byte-for-byte the benign one, so decompressing normally
            # yields the benign package and reveals nothing. The appended block
            # is what makes the file's sha512 drift from the pinned value, and it
            # is the flag XORed with keystream(pinned integrity of this dep).
            trailer = seal(FLAG, pinned_integrity)
            shipped = benign + trailer
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
