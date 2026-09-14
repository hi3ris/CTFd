#!/usr/bin/env python3
"""Reference solver for 'mask-slip'.

GitHub Actions masks only the *literal* secret in logs. The workflow pipes the
secret through ``base64``, so that output escapes masking. We read ``run.log``,
find the line produced by the ``base64`` step, base64-decode it, and recover the
secret (the flag).

Pure standard library.
"""

import base64
import binascii
import os
import re


def solve(root: str) -> str:
    with open(os.path.join(root, "run.log"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    # The base64 step's output is the log line right after the group header that
    # mentions "base64". Fall back to scanning every line for a decodable blob.
    candidates = []
    in_b64_group = False
    for line in lines:
        payload = line.split("Z", 1)[-1].strip() if "Z" in line else line.strip()
        if "##[group]" in line:
            in_b64_group = "base64" in line
            continue
        if "##[endgroup]" in line:
            in_b64_group = False
            continue
        if in_b64_group and payload:
            candidates.append(payload)

    for token in candidates:
        if not re.fullmatch(r"[A-Za-z0-9+/=]+", token):
            continue
        try:
            secret = base64.b64decode(token, validate=True).decode()
        except (binascii.Error, UnicodeDecodeError):
            continue
        if secret.startswith("NCTF{"):
            print("[+] leaked base64 in log:", token)
            print("[+] FLAG =", secret)
            return secret
    raise SystemExit("no decodable secret found in log")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
