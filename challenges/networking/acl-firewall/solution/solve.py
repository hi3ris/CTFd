#!/usr/bin/env python3
"""Evaluate the ACL against each flow and read the allowed tags in id order."""

import ipaddress
import json
import os


def ip_in(addr, cidr):
    return ipaddress.ip_address(addr) in ipaddress.ip_network(cidr, strict=False)


def matches(rule, flow):
    if not ip_in(flow["src"], rule["src"]):
        return False
    if not ip_in(flow["dst"], rule["dst"]):
        return False
    if rule["proto"] != "any" and rule["proto"] != flow["proto"]:
        return False
    if rule["dport"] != "any" and int(rule["dport"]) != flow["dport"]:
        return False
    return True


def evaluate(rules, flow):
    for r in rules:
        if matches(r, flow):
            return r["action"]
    return "deny"  # implicit default deny


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    doc = json.load(open(os.path.join(here, "..", "ruleset.json")))
    rules = doc["rules"]
    allowed = [f for f in doc["flows"] if evaluate(rules, f) == "allow"]
    allowed.sort(key=lambda f: f["id"])
    print("".join(f["tag"] for f in allowed))


if __name__ == "__main__":
    main()
