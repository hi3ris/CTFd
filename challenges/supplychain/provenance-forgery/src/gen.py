#!/usr/bin/env python3
"""Generate the provenance-forgery artifact bundle.

Each release ships a SLSA-style provenance statement signed with a homemade,
weak scheme: sig = sha256(KEY || "\\n" || subject_digest). The signing key is
leaked in a committed CI file, so any provenance can be verified (and forged)
offline. One release's provenance is FORGED — its signature does not validate
under the real key, and its artifact digest doesn't match. That release's
artifact carries the flag.
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

FLAG = "NCTF{w3ak_provenance_sig_forged_release_4e7a}"

KEY = b"acme-ci-hmac-key-DO-NOT-SHIP-v1"


def sign(subject_digest):
    return hashlib.sha256(KEY + b"\n" + subject_digest.encode()).hexdigest()


def make_artifact(path, payload):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        info = tarfile.TarInfo("dist/app.js")
        data = payload
        info.size = len(data)
        info.mtime = 0
        tar.addfile(info, io.BytesIO(data))
    body = gzip.compress(raw.getvalue(), mtime=0)
    with open(path, "wb") as fh:
        fh.write(body)
    return body


def build():
    os.makedirs(os.path.join(OUT, "provenance"), exist_ok=True)

    releases = [
        ("acme-app-1.0.0.tgz", b"module.exports = 1;\n", True),
        ("acme-app-1.1.0.tgz", b"module.exports = 2;\n", True),
        (
            "acme-app-1.2.0.tgz",
            b"// hotfix build\nvar _t = '" + base64.b64encode(FLAG.encode()) + b"';\n",
            False,  # forged provenance
        ),
        ("acme-app-1.3.0.tgz", b"module.exports = 4;\n", True),
    ]

    for name, payload, legit in releases:
        body = make_artifact(os.path.join(OUT, name), payload)
        digest = hashlib.sha256(body).hexdigest()
        version = name.split("-")[-1].rsplit(".", 1)[0]

        if legit:
            recorded_digest = digest
            sig = sign(digest)
        else:
            # Attacker shipped a different artifact than the one signed and
            # could not produce a valid signature without the key.
            recorded_digest = hashlib.sha256(b"decoy-build").hexdigest()
            sig = "0" * 64

        statement = {
            "_type": "https://in-toto.io/Statement/v1",
            "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [
                {"name": name, "digest": {"sha256": recorded_digest}},
            ],
            "predicate": {
                "buildDefinition": {"buildType": "acme/npm@v1"},
                "runDetails": {"builder": {"id": "acme-ci"}},
            },
            "signature": {"keyid": "acme-ci-2024", "sig": sig},
        }
        with open(os.path.join(OUT, "provenance", f"{version}.intoto.json"), "w") as fh:
            json.dump(statement, fh, indent=2)
            fh.write("\n")

    # The leaked signing key, as if committed by mistake into CI config.
    with open(os.path.join(OUT, "ci-signing.key"), "wb") as fh:
        fh.write(b"# ACME CI provenance signing key (leaked)\n")
        fh.write(b"SIGNING_KEY=" + KEY + b"\n")
        fh.write(b"# scheme: sig = sha256(SIGNING_KEY || 0x0a || subject.sha256)\n")

    print("built provenance-forgery artifacts")


if __name__ == "__main__":
    build()
