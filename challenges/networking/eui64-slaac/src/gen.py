#!/usr/bin/env python3
"""Generate the EUI-64 / SLAAC host inventory artifact.

Each host advertises a 48-bit MAC and shares one common /64 prefix. The SLAAC
interface identifier is derived from the MAC by the EUI-64 rule:

    * flip the universal/local bit (bit 0x02 of the first octet), and
    * insert 0xFF 0xFE between the OUI (bytes 0-2) and NIC (bytes 3-5) halves.

When the hosts are sorted by their resulting full IPv6 address, each host's
one-character ``tag`` field spells the flag in order. The artifact ships the
hosts shuffled, so the player must actually perform the EUI-64 transform to
recover the ordering.
"""

import json
import os
import random

FLAG = "NCTF{eui64_slaac_ll_bit_flip}"
PREFIX = "2001:db8:ac1d:64::"


def mac_to_eui64(mac):
    b = [int(x, 16) for x in mac.split(":")]
    b[0] ^= 0x02
    iid = b[0:3] + [0xFF, 0xFE] + b[3:6]
    return iid


def full_addr(prefix, iid):
    # prefix like "2001:db8:ac1d:64::" -> expand to 4 leading hextets
    head = prefix.rstrip(":").split(":")
    parts = []
    for x in head:
        parts.append(int(x, 16))
    while len(parts) < 4:
        parts.append(0)
    words = []
    for i in range(0, 8, 2):
        words.append((iid[i] << 8) | iid[i + 1])
    return tuple(parts[:4] + words)


def rand_mac(rng):
    return ":".join("%02x" % rng.randint(0, 255) for _ in range(6))


def main():
    rng = random.Random(0x64C0DE)
    n = len(FLAG)

    # Generate n distinct MACs and their sort keys, then assign flag chars to
    # the sorted order so that address-order spells the flag.
    hosts = []
    seen = set()
    while len(hosts) < n:
        mac = rand_mac(rng)
        if mac in seen:
            continue
        seen.add(mac)
        iid = mac_to_eui64(mac)
        key = full_addr(PREFIX, iid)
        hosts.append({"mac": mac, "key": key})

    hosts.sort(key=lambda h: h["key"])
    for h, ch in zip(hosts, FLAG):
        h["tag"] = ch

    out = []
    for i, h in enumerate(hosts):
        out.append({"host": "node-%02d" % i, "mac": h["mac"], "tag": h["tag"]})
    rng.shuffle(out)

    doc = {
        "prefix": PREFIX + "/64",
        "note": "SLAAC autoconfig inventory; interface IDs omitted on purpose.",
        "hosts": out,
    }

    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "hosts.json")
    with open(dest, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print("wrote", os.path.normpath(dest), "with", len(out), "hosts")


if __name__ == "__main__":
    main()
