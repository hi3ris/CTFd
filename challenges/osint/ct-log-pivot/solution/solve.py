#!/usr/bin/env python3
"""Pivot from the CT log to a cert.tg subdomain absent from the public zone,
then base32-decode that host's TXT record from the resolver cache."""

import base64
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
APEX = "cert.tg"


def zone_hosts() -> set:
    hosts = {APEX}
    for line in open(os.path.join(ROOT, "cert.tg.zone")):
        line = line.strip()
        if not line or line.startswith(("$", ";")) or "(" in line or ")" in line:
            continue
        label = line.split()[0]
        if label in ("@", "IN"):
            continue
        if not re.match(r"^[A-Za-z0-9_-]+$", label):
            continue
        hosts.add(f"{label}.{APEX}")
    return hosts


def ct_subdomains() -> set:
    found = set()
    for line in open(os.path.join(ROOT, "ct-log.txt")):
        if line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5:
            continue
        status, sans = parts[1], parts[4]
        if status != "valid":
            continue
        for san in sans.split(","):
            san = san.strip()
            if san.endswith(APEX) and "*" not in san:
                found.add(san)
    return found


def txt_records() -> dict:
    recs = {}
    for line in open(os.path.join(ROOT, "resolver_cache.txt")):
        if line.startswith(";"):
            continue
        cols = line.split("\t")
        if len(cols) >= 5 and cols[3] == "TXT":
            recs[cols[0].rstrip(".")] = cols[4].strip().strip('"')
    return recs


def main() -> None:
    known = zone_hosts()
    shadow = ct_subdomains() - known
    txt = txt_records()

    for host in shadow:
        data = txt.get(host)
        if not data or not data.startswith("nctf-b32="):
            continue
        decoded = base64.b32decode(data.split("=", 1)[1]).decode()
        if decoded.startswith("NCTF{"):
            print(decoded)
            return
    raise SystemExit("flag not found")


if __name__ == "__main__":
    main()
