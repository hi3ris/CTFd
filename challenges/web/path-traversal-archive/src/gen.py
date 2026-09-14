#!/usr/bin/env python3
"""Producer for path-traversal-archive (rebuilds webroot.tar.gz)."""

import io
import os
import tarfile

FLAG = "NCTF{dot_dot_slash_reads_the_service_secret}"

FILES = {
    "deploy/public/index.html": b"<!doctype html><title>Static Assets</title><h1>Asset CDN</h1>\n",
    "deploy/public/style.css": b"body{font-family:sans-serif}\n",
    "deploy/public/robots.txt": b"User-agent: *\nDisallow: /\n",
    "deploy/private/service.env": (
        b"# NOT web-accessible. One level above ./public.\n"
        b"DB_PASSWORD=hunter2-rotate-me\n"
        b"INTERNAL_FLAG=" + FLAG.encode() + b"\n"
    ),
}


def main() -> None:
    with tarfile.open("webroot.tar.gz", "w:gz") as t:
        for name, data in FILES.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    print("wrote", os.path.abspath("webroot.tar.gz"))


if __name__ == "__main__":
    main()
