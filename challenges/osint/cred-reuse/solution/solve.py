#!/usr/bin/env python3
"""Crack the forum hashes with the wordlist, find the email reused on the
admin-portal, and decrypt admin_portal.enc with that password."""

import csv
import hashlib
import os
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def keystream(password: str, n: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(password.encode() + counter.to_bytes(4, "big")).digest()
        counter += 1
    return bytes(out[:n])


def main() -> None:
    words = open(os.path.join(ROOT, "wordlist.txt")).read().split()
    by_hash = {hashlib.sha1(w.encode()).hexdigest(): w for w in words}

    cracked = {}
    for line in open(os.path.join(ROOT, "dump.txt")):
        email, h = line.strip().split(":")
        if h in by_hash:
            cracked[email] = by_hash[h]

    services = defaultdict(set)
    with open(os.path.join(ROOT, "services.csv")) as fh:
        for row in csv.DictReader(fh):
            services[row["email"]].add(row["service"])

    # the reused credential: cracked, on the forum, and on the admin-portal
    reused_email = next(e for e in cracked if {"forum", "admin-portal"} <= services[e])
    password = cracked[reused_email]

    ct = open(os.path.join(ROOT, "admin_portal.enc"), "rb").read()
    pt = bytes(a ^ b for a, b in zip(ct, keystream(password, len(ct)))).decode()
    flag = next(line.split(": ", 1)[1] for line in pt.splitlines() if "jeton" in line)
    print(flag)


if __name__ == "__main__":
    main()
