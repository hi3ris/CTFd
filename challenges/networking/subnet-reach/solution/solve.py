#!/usr/bin/env python3
"""Longest-prefix-match each packet; read tags of packets that reach the host."""

import ipaddress
import json
import os


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
    here = os.path.dirname(os.path.abspath(__file__))
    doc = json.load(open(os.path.join(here, "..", "routing.json")))
    routes = doc["routes"]
    reach = [p for p in doc["packets"] if lpm(routes, p["dst"]) == "local"]
    reach.sort(key=lambda p: p["id"])
    print("".join(p["tag"] for p in reach))


if __name__ == "__main__":
    main()
