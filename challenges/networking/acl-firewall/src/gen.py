#!/usr/bin/env python3
"""Generate an ordered firewall ACL and a set of candidate flows.

The device evaluates rules top-to-bottom, first-match-wins, with an implicit
default-DENY at the end. Each flow carries a one-character ``tag``. The flows
that are ultimately ALLOWED, read in ascending flow-id order, spell the flag.
Denied flows carry decoy characters.
"""

import ipaddress
import json
import os
import random

FLAG = "NCTF{acl_first_match_wins_default_deny}"


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
    return "deny"


def main():
    rng = random.Random(0xF117A11)

    rules = [
        {
            "src": "10.10.0.0/16",
            "dst": "10.20.0.0/16",
            "proto": "tcp",
            "dport": "22",
            "action": "deny",
        },
        {
            "src": "10.10.0.0/16",
            "dst": "10.20.0.0/16",
            "proto": "tcp",
            "dport": "443",
            "action": "allow",
        },
        {
            "src": "10.10.0.0/16",
            "dst": "10.20.0.0/16",
            "proto": "tcp",
            "dport": "any",
            "action": "deny",
        },
        {
            "src": "192.168.0.0/16",
            "dst": "10.20.0.0/16",
            "proto": "udp",
            "dport": "53",
            "action": "allow",
        },
        {
            "src": "192.168.0.0/16",
            "dst": "0.0.0.0/0",
            "proto": "any",
            "dport": "any",
            "action": "deny",
        },
        {
            "src": "172.16.5.0/24",
            "dst": "10.20.7.0/24",
            "proto": "tcp",
            "dport": "8443",
            "action": "allow",
        },
        {
            "src": "0.0.0.0/0",
            "dst": "10.20.0.0/16",
            "proto": "icmp",
            "dport": "any",
            "action": "allow",
        },
    ]

    # Build flows so that ALLOWED ones (in id order) spell FLAG.
    flows = []
    fid = 0

    def add_allowed(ch):
        nonlocal fid
        choice = rng.choice(["https", "dns", "alt", "icmp"])
        if choice == "https":
            f = {
                "src": "10.10.%d.%d" % (rng.randint(0, 255), rng.randint(1, 254)),
                "dst": "10.20.%d.%d" % (rng.randint(0, 255), rng.randint(1, 254)),
                "proto": "tcp",
                "dport": 443,
            }
        elif choice == "dns":
            f = {
                "src": "192.168.%d.%d" % (rng.randint(0, 255), rng.randint(1, 254)),
                "dst": "10.20.%d.%d" % (rng.randint(0, 255), rng.randint(1, 254)),
                "proto": "udp",
                "dport": 53,
            }
        elif choice == "alt":
            f = {
                "src": "172.16.5.%d" % rng.randint(1, 254),
                "dst": "10.20.7.%d" % rng.randint(1, 254),
                "proto": "tcp",
                "dport": 8443,
            }
        else:
            f = {
                "src": "203.0.113.%d" % rng.randint(1, 254),
                "dst": "10.20.%d.%d" % (rng.randint(0, 255), rng.randint(1, 254)),
                "proto": "icmp",
                "dport": 0,
            }
        f.update({"id": fid, "tag": ch})
        assert evaluate(rules, f) == "allow", f
        flows.append(f)
        fid += 1

    def add_denied(ch):
        nonlocal fid
        choice = rng.choice(["ssh", "other", "extern"])
        if choice == "ssh":
            f = {
                "src": "10.10.%d.%d" % (rng.randint(0, 255), rng.randint(1, 254)),
                "dst": "10.20.%d.%d" % (rng.randint(0, 255), rng.randint(1, 254)),
                "proto": "tcp",
                "dport": 22,
            }
        elif choice == "other":
            f = {
                "src": "10.10.%d.%d" % (rng.randint(0, 255), rng.randint(1, 254)),
                "dst": "10.20.%d.%d" % (rng.randint(0, 255), rng.randint(1, 254)),
                "proto": "tcp",
                "dport": 8080,
            }
        else:
            f = {
                "src": "192.168.%d.%d" % (rng.randint(0, 255), rng.randint(1, 254)),
                "dst": "8.8.8.8",
                "proto": "tcp",
                "dport": 443,
            }
        f.update({"id": fid, "tag": ch})
        assert evaluate(rules, f) == "deny", f
        flows.append(f)
        fid += 1

    decoy_pool = list("zyxqvkjw0123abcd")
    di = 0
    for ch in FLAG:
        add_allowed(ch)
        # sprinkle 0-2 denied decoys between allowed flows
        for _ in range(rng.randint(0, 2)):
            add_denied(decoy_pool[di % len(decoy_pool)])
            di += 1

    rng.shuffle(flows)

    doc = {
        "policy": "first-match-wins; implicit default DENY",
        "rules": rules,
        "flows": flows,
    }
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "ruleset.json")
    with open(dest, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print(
        "wrote", os.path.normpath(dest), "rules=%d flows=%d" % (len(rules), len(flows))
    )


if __name__ == "__main__":
    main()
