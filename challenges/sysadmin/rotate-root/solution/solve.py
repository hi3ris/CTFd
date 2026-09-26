#!/usr/bin/env python3
"""Reference solver for 'rotate-root'.

The privilege path is: logrotate's ``postrotate`` runs ``rotate-hook.sh`` as root
(and sudoers lets ``deploy`` trigger it too). The hook sources ``rotate.conf``
and both writes to, and *derives the value for*, a token file:

    OUT   = "$SECRET_DIR/app-$CYCLE-$HOSTID.token"
    TOKEN = sha256("$CYCLE:$HOSTID:$ROTATE_SECRET")[:10 hex]

The token file itself is not shipped, so we reconstruct the token from the four
config values and wrap it in the flag format.

Pure standard library.
"""

import hashlib
import os


def read_conf(path: str) -> dict:
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def solve(root: str) -> str:
    fs = os.path.join(root, "fs")
    conf = read_conf(os.path.join(fs, "etc", "app", "rotate.conf"))
    cycle = conf["CYCLE"]
    hostid = conf["HOSTID"]
    secret = conf["ROTATE_SECRET"]

    # Naming rule from rotate-hook.sh (informational -- the file is not shipped):
    name = f"app-{cycle}-{hostid}.token"
    token_path = conf["SECRET_DIR"].rstrip("/") + "/" + name
    print(f"[+] root-written (unshipped) token path: {token_path}")

    # Derivation rule from rotate-hook.sh:
    #   TOKEN = sha256("CYCLE:HOSTID:ROTATE_SECRET")[:10 hex]
    material = f"{cycle}:{hostid}:{secret}"
    token = hashlib.sha256(material.encode()).hexdigest()[:10]
    print("[+] derived rotation token:", token)

    flag = "NCTF{logrotate_postrotate_root_" + token + "}"
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
