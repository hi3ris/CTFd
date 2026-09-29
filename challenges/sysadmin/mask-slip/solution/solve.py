#!/usr/bin/env python3
"""Reference solver for 'mask-slip'.

GitHub Actions masks only the *literal* secret in logs. This pipeline pipes the
secret through ``xxd -p`` (a hex dump) "for debugging", so that output escapes
masking. We scan ``run.log`` for the leaked line, hex-decode it, and recover the
secret (the flag). Note the leak is hex, not base64 -- a ``TkNURn`` / base64
prefix grep finds nothing.

Pure standard library.
"""

import binascii
import os
import re


def solve(root: str) -> str:
    with open(os.path.join(root, "run.log"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    # Strip the leading "<timestamp>Z " prefix from each log line.
    def payload(line: str) -> str:
        return line.split("Z", 1)[-1].strip() if "Z" in line else line.strip()

    # Primary path: the leak is the output of the step whose group header
    # mentions the hex-dump command (xxd). Fall back to scanning every line.
    candidates = []
    in_leak_group = False
    for line in lines:
        if "##[group]" in line:
            in_leak_group = "xxd" in line or "hex" in line.lower()
            continue
        if "##[endgroup]" in line:
            in_leak_group = False
            continue
        p = payload(line)
        if in_leak_group and p:
            candidates.insert(0, p)  # prefer the leak group's lines
        elif p:
            candidates.append(p)

    for token in candidates:
        if len(token) % 2 or not re.fullmatch(r"[0-9a-fA-F]+", token):
            continue
        try:
            secret = binascii.unhexlify(token).decode()
        except (binascii.Error, UnicodeDecodeError):
            continue
        if secret.startswith("NCTF{"):
            print("[+] leaked hex in log:", token)
            print("[+] FLAG =", secret)
            return secret
    raise SystemExit("no decodable secret found in log")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
