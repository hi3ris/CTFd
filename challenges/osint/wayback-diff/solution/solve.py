#!/usr/bin/env python3
"""Diff consecutive snapshots, find the base64 token that was added and then
removed (a line deleted between captures), and decode it."""

import base64
import glob
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

B64 = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")


def tokens(text: str) -> set:
    return set(B64.findall(text))


def main() -> None:
    files = sorted(glob.glob(os.path.join(ROOT, "snapshot_*.html")))
    contents = [open(f).read() for f in files]

    # a token that exists in some snapshot but is absent from a LATER one = scrubbed
    scrubbed = set()
    for i in range(len(contents) - 1):
        removed = tokens(contents[i]) - tokens(contents[i + 1])
        scrubbed |= removed

    for tok in scrubbed:
        try:
            decoded = base64.b64decode(tok).decode()
        except (ValueError, UnicodeDecodeError):
            continue
        if decoded.startswith("NCTF{"):
            print(decoded)
            return
    raise SystemExit("flag not found")


if __name__ == "__main__":
    main()
