#!/usr/bin/env python3
"""Recover the flag from the layered-image-leak bundle.

A later layer whiteouts `app/config/secret.env`, so it is gone from the flattened
filesystem. But the bytes still live in the earlier layer that added it. Read
the layers in order, confirm the whiteout, then pull the secret from the layer
that introduced it.
"""

import base64
import io
import json
import os
import re
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TARGET = "app/config/secret.env"


def main():
    outer = tarfile.open(os.path.join(ROOT, "image.tar"))
    manifest = json.load(outer.extractfile("manifest.json"))
    layer_paths = manifest[0]["Layers"]

    whiteouted = False
    found = None
    for lp in layer_paths:
        lt = outer.extractfile(lp).read()
        with tarfile.open(fileobj=io.BytesIO(lt)) as layer:
            names = layer.getnames()
            if "app/config/.wh.secret.env" in names:
                whiteouted = True
            if TARGET in names and found is None:
                found = layer.extractfile(TARGET).read().decode()

    assert whiteouted, "expected a whiteout hiding the secret in the final fs"
    assert found is not None, "secret.env should survive in an earlier layer"

    b64 = re.search(r"DEPLOY_KEY=(\S+)", found).group(1)
    flag = base64.b64decode(b64).decode()
    print(flag)


if __name__ == "__main__":
    main()
