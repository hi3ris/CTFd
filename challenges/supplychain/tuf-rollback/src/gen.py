#!/usr/bin/env python3
"""Generate the tuf-rollback artifact bundle.

A TUF-style update repository. The signed `timestamp` says the current snapshot
is version 8, but the served `snapshot.json` is version 5 — a rollback attack.
The stale snapshot pins targets version 5, which points at a backdoored
`updater-agent`. The newer (version 8) targets metadata is clean. The malicious
pinned artifact carries the flag.
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

FLAG = "NCTF{tuf_rollback_pinned_evil_release_b0a2}"


def make_tgz(path, inner, data):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        info = tarfile.TarInfo(inner)
        info.size = len(data)
        info.mtime = 0
        tar.addfile(info, io.BytesIO(data))
    body = gzip.compress(raw.getvalue(), mtime=0)
    with open(path, "wb") as fh:
        fh.write(body)
    return body


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def write_json(name, signed):
    doc = {"signed": signed, "signatures": [{"keyid": "acme-tuf", "sig": "de:ad"}]}
    body = json.dumps(doc, indent=2, sort_keys=True).encode()
    with open(os.path.join(OUT, name), "wb") as fh:
        fh.write(body)
    return body


def build():
    os.makedirs(os.path.join(OUT, "targets"), exist_ok=True)

    # Backdoored old agent (pinned by the rolled-back snapshot) holds the flag.
    evil = make_tgz(
        os.path.join(OUT, "targets", "updater-agent-2.0.1.tgz"),
        "agent.py",
        b"# updater agent\n_c = '" + base64.b64encode(FLAG.encode()) + b"'\n",
    )
    # Clean current agent (referenced only by the newer targets metadata).
    good = make_tgz(
        os.path.join(OUT, "targets", "updater-agent-2.1.0.tgz"),
        "agent.py",
        b"# updater agent\nprint('ok')\n",
    )

    targets_v5 = write_json(
        "targets-v5.json",
        {
            "_type": "targets",
            "version": 5,
            "targets": {
                "updater-agent-2.0.1.tgz": {
                    "length": len(evil),
                    "hashes": {"sha256": sha256(evil)},
                }
            },
        },
    )
    targets_v8 = write_json(
        "targets-v8.json",
        {
            "_type": "targets",
            "version": 8,
            "targets": {
                "updater-agent-2.1.0.tgz": {
                    "length": len(good),
                    "hashes": {"sha256": sha256(good)},
                }
            },
        },
    )

    # Served snapshot is version 5 (stale) and pins targets version 5.
    write_json(
        "snapshot.json",
        {
            "_type": "snapshot",
            "version": 5,
            "meta": {
                "targets.json": {
                    "version": 5,
                    "hashes": {"sha256": sha256(targets_v5)},
                }
            },
        },
    )

    # Timestamp (freshest role) knows the current snapshot is version 8.
    write_json(
        "timestamp.json",
        {
            "_type": "timestamp",
            "version": 12,
            "meta": {
                "snapshot.json": {
                    "version": 8,
                    "hashes": {"sha256": sha256(targets_v8)},
                }
            },
        },
    )

    print("built tuf-rollback artifacts")


if __name__ == "__main__":
    build()
