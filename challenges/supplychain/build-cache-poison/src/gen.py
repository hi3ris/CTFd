#!/usr/bin/env python3
"""Generate the build-cache-poison artifact bundle.

A Makefile fetches vendored dependencies into a build cache. Every fetch is
checksum-verified against `checksums.sha256` except one, which is pulled with
no integrity check. That un-verified cache entry has been poisoned and carries
the flag (XOR + base64).
"""

import base64
import gzip
import hashlib
import io
import os
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

FLAG = "NCTF{build_cache_no_checksum_pull_8d3f}"
XOR_KEY = 0x3C


def make_tgz(path, inner_name, data):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        info = tarfile.TarInfo(inner_name)
        info.size = len(data)
        info.mtime = 0
        tar.addfile(info, io.BytesIO(data))
    body = gzip.compress(raw.getvalue(), mtime=0)
    with open(path, "wb") as fh:
        fh.write(body)
    return body


def build():
    cache = os.path.join(OUT, "vendor-cache")
    os.makedirs(cache, exist_ok=True)

    # (artifact, cdn url, verified?)
    deps = [
        ("libcrc-1.0.tar.gz", "https://cdn.acme.dev/libcrc-1.0.tar.gz", True),
        ("libui-2.3.tar.gz", "https://cdn.acme.dev/libui-2.3.tar.gz", True),
        ("libnet-0.9.tar.gz", "http://mirror.build-cache.dev/libnet-0.9.tar.gz", False),
        ("libz-1.2.tar.gz", "https://cdn.acme.dev/libz-1.2.tar.gz", True),
    ]

    checksum_lines = []
    recipes = []
    for artifact, url, verified in deps:
        if verified:
            data = f"/* vendored {artifact} */\n".encode()
            body = make_tgz(os.path.join(cache, artifact), "src.c", data)
            checksum_lines.append(f"{hashlib.sha256(body).hexdigest()}  {artifact}")
            recipe = (
                f"vendor-cache/{artifact}:\n"
                f"\tcurl -fsSL -o $@ {url}\n"
                f"\tsha256sum --ignore-missing -c checksums.sha256\n"
            )
        else:
            # Poisoned: XOR then base64 the flag into the payload.
            xored = bytes(b ^ XOR_KEY for b in FLAG.encode())
            payload = b"BUILD_TOKEN=" + base64.b64encode(xored) + b"\n"
            make_tgz(os.path.join(cache, artifact), "build.env", payload)
            recipe = f"vendor-cache/{artifact}:\n" f"\tcurl -fsSL -o $@ {url}\n"
        recipes.append(recipe)

    makefile = (
        "# ACME vendored-dependency fetcher\n"
        "# Downloads pinned artifacts into vendor-cache/.\n"
        f"XOR_KEY := {XOR_KEY}\n\n"
        "ARTIFACTS := " + " ".join(f"vendor-cache/{a}" for a, _, _ in deps) + "\n\n"
        ".PHONY: fetch\n"
        "fetch: $(ARTIFACTS)\n\n" + "\n".join(recipes)
    )
    with open(os.path.join(OUT, "Makefile"), "w") as fh:
        fh.write(makefile)

    with open(os.path.join(OUT, "checksums.sha256"), "w") as fh:
        fh.write("\n".join(checksum_lines) + "\n")

    print("built build-cache-poison artifacts")


if __name__ == "__main__":
    build()
