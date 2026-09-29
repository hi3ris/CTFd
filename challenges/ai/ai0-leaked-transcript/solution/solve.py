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


def _deobfuscate(token: str):
    """A leaked token is base64( reverse(flag) ). Return the flag, or None if
    the blob is not a valid obfuscated NCTF flag."""
    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except Exception:
        return None
    flag = decoded[::-1]
    return flag if flag.startswith("NCTF{") and flag.endswith("}") else None


def solve(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompt = data["metadata"]["runtime_config"]["system_prompt"]

    # The leaked config is NOISY: it carries a rotated-out DECOY token as well
    # as the current one. Decode EVERY base64 blob and discriminate, rather
    # than grabbing the first one we see.
    candidates = re.findall(r"([A-Za-z0-9+/]{16,}={0,2})", prompt)
    decoded = [(tok, _deobfuscate(tok)) for tok in candidates]
    valid = [(tok, flag) for tok, flag in decoded if flag]

    # Each token sits on its own operational-note line. Judge a token by the
    # text of ITS line: reject one tagged DEPRECATED / ROTATED / previous /
    # no longer valid; keep the one called "current".
    def line_of(tok: str) -> str:
        for line in prompt.splitlines():
            if tok in line:
                return line.upper()
        return ""

    def is_rotated(tok: str) -> bool:
        line = line_of(tok)
        return any(
            w in line for w in ("DEPRECATED", "ROTATED", "PREVIOUS", "NO LONGER VALID")
        )

    current = [flag for tok, flag in valid if not is_rotated(tok)]
    if current:
        return current[0]
    # Fallback: any valid flag we could recover.
    return valid[0][1] if valid else ""


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    default = os.path.join(here, os.pardir, "public", "transcript.json")
    path = sys.argv[1] if len(sys.argv) > 1 else default
    print(solve(path))
