#!/usr/bin/env python3
"""
Solver for ai0-leaked-transcript.

Pull the leaked system_prompt out of the exported transcript's metadata,
grab the "audit-handoff token", base64-decode it, and reverse it to recover
the flag.
"""
import base64
import json
import os
import re
import sys


def solve(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompt = data["metadata"]["runtime_config"]["system_prompt"]

    # The token is the base64 blob following "token for this deployment is".
    m = re.search(r"token for this deployment is\s+([A-Za-z0-9+/=]+)", prompt)
    if not m:
        # Fallback: any long-ish base64 run in the prompt.
        m = re.search(r"([A-Za-z0-9+/]{16,}={0,2})", prompt)
    token = m.group(1)

    decoded = base64.b64decode(token).decode("utf-8")
    flag = decoded[::-1]  # de-obfuscate: it was base64(reverse(flag))
    return flag


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    default = os.path.join(here, os.pardir, "public", "transcript.json")
    path = sys.argv[1] if len(sys.argv) > 1 else default
    print(solve(path))
