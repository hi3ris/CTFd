#!/usr/bin/env python3
"""Generate the layered-image-leak artifact bundle.

Builds a `docker save`-style image tar (legacy layout). A secret file is added
in an early layer, then "deleted" in a later layer via an overlayfs whiteout
(`.wh.secret.env`). The delete only hides the file in the final filesystem; the
bytes still live in the earlier layer blob. That secret holds the flag.
"""

import base64
import hashlib
import io
import json
import os
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

FLAG = "NCTF{d0cker_layer_secret_survives_rm_6c15}"


def layer_tar(entries):
    """Build one layer.tar; entries is list of (path, data|None). None=whiteout."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for path, data in entries:
            info = tarfile.TarInfo(path)
            info.mtime = 0
            info.size = len(data) if data is not None else 0
            tar.addfile(info, io.BytesIO(data or b""))
    return buf.getvalue()


def build():
    secret_val = base64.b64encode(FLAG.encode()).decode()
    secret_body = f"DEPLOY_KEY={secret_val}\n".encode()

    layers = [
        # layer 0: seed config, includes the secret
        [
            ("app/", None),
            ("app/config/", None),
            ("app/config/secret.env", secret_body),
        ],
        # layer 1: application code
        [
            ("app/server.js", b"console.log('acme app up');\n"),
        ],
        # layer 2: "remove" the secret (overlayfs whiteout)
        [
            ("app/config/.wh.secret.env", b""),
        ],
    ]

    manifest_layers = []
    diff_ids = []
    with tarfile.open(os.path.join(OUT, "image.tar"), "w") as outer:

        def add(name, data):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            outer.addfile(info, io.BytesIO(data))

        for i, entries in enumerate(layers):
            lt = layer_tar(entries)
            layer_id = hashlib.sha256(lt + str(i).encode()).hexdigest()
            add(f"{layer_id}/VERSION", b"1.0")
            add(
                f"{layer_id}/json",
                json.dumps(
                    {"id": layer_id, "created": "1970-01-01T00:00:00Z"}
                ).encode(),
            )
            add(f"{layer_id}/layer.tar", lt)
            manifest_layers.append(f"{layer_id}/layer.tar")
            diff_ids.append("sha256:" + hashlib.sha256(lt).hexdigest())

        config = {
            "architecture": "amd64",
            "os": "linux",
            "config": {"Env": ["PATH=/usr/bin"], "Cmd": ["node", "app/server.js"]},
            "rootfs": {"type": "layers", "diff_ids": diff_ids},
            "history": [
                {"created_by": "ADD config"},
                {"created_by": "COPY app code"},
                {"created_by": "RUN rm app/config/secret.env"},
            ],
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(0)),
        }
        config_bytes = json.dumps(config, indent=2).encode()
        config_id = hashlib.sha256(config_bytes).hexdigest()
        add(f"{config_id}.json", config_bytes)

        manifest = [
            {
                "Config": f"{config_id}.json",
                "RepoTags": ["acme/app:latest"],
                "Layers": manifest_layers,
            }
        ]
        add("manifest.json", json.dumps(manifest, indent=2).encode())
        add("repositories", json.dumps({"acme/app": {"latest": layer_id}}).encode())

    print("built layered-image-leak artifacts")


if __name__ == "__main__":
    build()
