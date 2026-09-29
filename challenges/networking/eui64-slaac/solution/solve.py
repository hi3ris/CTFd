#!/usr/bin/env python3
"""Recover the flag from hosts.json by deriving each host's SLAAC address.

For every host, apply the EUI-64 rule to its MAC (flip the U/L bit, insert
ff:fe), build the full 128-bit IPv6 address under the shared prefix, sort the
hosts by that address, and read the ``tag`` field of each in order.
"""

import json
import os


def mac_to_eui64(mac):
    b = [int(x, 16) for x in mac.split(":")]
    b[0] ^= 0x02
    return b[0:3] + [0xFF, 0xFE] + b[3:6]


def full_addr(prefix, iid):
    head = prefix.split("/")[0].rstrip(":").split(":")
    parts = [int(x, 16) for x in head]
    while len(parts) < 4:
        parts.append(0)
    words = [(iid[i] << 8) | iid[i + 1] for i in range(0, 8, 2)]
    return tuple(parts[:4] + words)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    doc = json.load(open(os.path.join(here, "..", "hosts.json")))
    prefix = doc["prefix"]
    hosts = doc["hosts"]
    for h in hosts:
        h["_key"] = full_addr(prefix, mac_to_eui64(h["mac"]))
    hosts.sort(key=lambda h: h["_key"])
    flag = "".join(h["tag"] for h in hosts)
    print(flag)


if __name__ == "__main__":
    main()
