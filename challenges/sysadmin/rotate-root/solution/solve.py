#!/usr/bin/env python3
"""Reference solver for 'rotate-root'.

The privilege path is: logrotate's ``postrotate`` runs ``rotate-hook.sh`` as root
(and sudoers lets ``deploy`` trigger it too). The hook sources ``rotate.conf``
and writes a token to a path it derives as::

    OUT = "$SECRET_DIR/app-$CYCLE-$HOSTID.token"

We parse those three values from ``rotate.conf``, apply the hook's naming rule to
find the token path, and read the flag out of the shipped ``fs/`` mirror.

Pure standard library.
"""

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
    secret_dir = conf["SECRET_DIR"]
    cycle = conf["CYCLE"]
    hostid = conf["HOSTID"]

    # Naming rule from rotate-hook.sh: app-<CYCLE>-<HOSTID>.token
    name = f"app-{cycle}-{hostid}.token"
    token_path = secret_dir.rstrip("/") + "/" + name
    print(f"[+] deduced root-written token path: {token_path}")

    local = os.path.join(fs, token_path.lstrip("/"))
    with open(local, encoding="utf-8") as fh:
        token = fh.read().strip()
    print("[+] raw rotation token:", token)
    flag = "NCTF{logrotate_postrotate_root_" + token + "}"
    print("[+] FLAG =", flag)
    return flag


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    solve(os.path.normpath(os.path.join(here, "..")))
