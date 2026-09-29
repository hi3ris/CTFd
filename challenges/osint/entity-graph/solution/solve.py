#!/usr/bin/env python3
"""Traverse the entity graph along VERIFIED links only, from the seed persona,
reconstruct the pivot path to the single reachable PERSON node, and DERIVE the
flag from that path. The flag is not stored in the CSVs -- you must actually
traverse the verified graph to compute it."""

import csv
import hashlib
import hmac
import os
from collections import defaultdict, deque

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

VERIFIED = {
    "same_email",
    "same_phone",
    "same_device",
    "owns_wallet",
    "registered_by",
    "confirmed_aka",
}
SEED = "h_seed"


def main() -> None:
    nodes = {}
    with open(os.path.join(ROOT, "nodes.csv"), newline="") as fh:
        for row in csv.DictReader(fh):
            nodes[row["id"]] = row

    adj = defaultdict(list)
    with open(os.path.join(ROOT, "edges.csv"), newline="") as fh:
        for row in csv.DictReader(fh):
            if row["relation"] in VERIFIED:
                # verified links are treated as undirected pivots
                adj[row["src"]].append(row["dst"])
                adj[row["dst"]].append(row["src"])

    parent = {SEED: None}
    q = deque([SEED])
    while q:
        cur = q.popleft()
        for nxt in adj[cur]:
            if nxt not in parent:
                parent[nxt] = cur
                q.append(nxt)

    persons = [n for n in parent if nodes[n]["type"] == "person"]
    assert len(persons) == 1, f"expected 1 person, got {persons}"
    target = persons[0]

    # reconstruct the ordered verified path seed -> target
    path = []
    node = target
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()

    material = "|".join(nodes[n]["value"] for n in path).encode()
    key = nodes[target]["label"].encode()
    body = hmac.new(key, material, hashlib.sha256).hexdigest()[:24]
    print(f"NCTF{{{body}}}")


if __name__ == "__main__":
    main()
