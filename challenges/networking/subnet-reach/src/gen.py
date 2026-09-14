#!/usr/bin/env python3
"""Generate a router forwarding table plus a list of probe packets.

Forwarding is longest-prefix-match. Each route has an action:

    * "local"  -> delivered onto the segment holding the target host
    * "gw:<ip>"-> forwarded to another next hop (does NOT reach the host)
    * "null0"  -> black-holed (dropped)

A packet reaches the target host iff its longest-matching route is "local".
Overlapping prefixes, a default route, and more-specific null0 black holes make
LPM mandatory. Each packet carries a one-character ``tag``; the reaching packets
read in ascending ``id`` order spell the flag.
"""

import ipaddress
import json
import os
import random

FLAG = "NCTF{longest_prefix_match_wins_and_null0_drops}"

ROUTES = [
    {"prefix": "0.0.0.0/0", "action": "gw:203.0.113.1"},
    {"prefix": "10.0.0.0/8", "action": "gw:10.255.0.1"},
    {"prefix": "10.0.7.0/24", "action": "local"},
    {"prefix": "10.0.7.128/25", "action": "gw:10.0.7.129"},
    {"prefix": "10.0.7.66/32", "action": "null0"},
    {"prefix": "10.0.0.0/16", "action": "gw:10.0.255.254"},
    {"prefix": "192.168.0.0/16", "action": "gw:192.168.1.1"},
    {"prefix": "172.16.0.0/12", "action": "null0"},
]


def lpm(routes, dst):
    ip = ipaddress.ip_address(dst)
    bestlen = -1
    action = None
    for r in routes:
        net = ipaddress.ip_network(r["prefix"])
        if ip in net and net.prefixlen > bestlen:
            bestlen = net.prefixlen
            action = r["action"]
    return action


def main():
    rng = random.Random(0x5B4E7)

    def reaching_dst():
        # in 10.0.7.0/24, low half (not .128/25), not the .66 black hole
        while True:
            host = rng.randint(1, 126)
            if host == 66:
                continue
            dst = "10.0.7.%d" % host
            if lpm(ROUTES, dst) == "local":
                return dst

    def non_reaching_dst():
        pool = [
            lambda: "10.0.7.%d" % rng.randint(129, 254),  # /25 -> gw
            lambda: "10.0.7.66",  # null0
            lambda: "10.0.%d.%d" % (rng.randint(1, 254), rng.randint(1, 254)),  # /16 gw
            lambda: "10.%d.%d.%d"
            % (rng.randint(1, 254), rng.randint(0, 254), rng.randint(1, 254)),  # /8 gw
            lambda: "172.16.%d.%d"
            % (rng.randint(0, 254), rng.randint(1, 254)),  # null0
            lambda: "192.168.%d.%d" % (rng.randint(0, 254), rng.randint(1, 254)),  # gw
            lambda: "8.8.%d.%d" % (rng.randint(0, 254), rng.randint(1, 254)),  # default
        ]
        while True:
            dst = rng.choice(pool)()
            if lpm(ROUTES, dst) != "local":
                return dst

    packets = []
    pid = 0
    decoy = list("xkq70zjvw9")
    di = 0
    for ch in FLAG:
        packets.append({"id": pid, "dst": reaching_dst(), "tag": ch})
        pid += 1
        for _ in range(rng.randint(0, 2)):
            packets.append(
                {"id": pid, "dst": non_reaching_dst(), "tag": decoy[di % len(decoy)]}
            )
            di += 1
            pid += 1

    rng.shuffle(packets)

    doc = {
        "target_host": "10.0.7.42",
        "forwarding": "longest-prefix-match; a packet reaches the host only if"
        " its best route action is 'local'",
        "routes": ROUTES,
        "packets": packets,
    }
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "routing.json")
    with open(dest, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print("wrote", os.path.normpath(dest), "packets=%d" % len(packets))


if __name__ == "__main__":
    main()
