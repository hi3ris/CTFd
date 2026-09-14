#!/usr/bin/env python3
"""Pick the best BGP route per prefix and read winners' labels in prefix order."""

import ipaddress
import json
import os

ORIGIN = {"igp": 0, "egp": 1, "incomplete": 2}


def rank(route):
    return (
        -route["local_pref"],
        len(route["as_path"]),
        ORIGIN[route["origin"]],
        route["med"],
        route["peer_id"],
    )


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    doc = json.load(open(os.path.join(here, "..", "bgp_rib.json")))
    entries = doc["rib"]
    entries.sort(key=lambda e: int(ipaddress.ip_network(e["prefix"]).network_address))
    flag = "".join(min(e["routes"], key=rank)["label"] for e in entries)
    print(flag)


if __name__ == "__main__":
    main()
