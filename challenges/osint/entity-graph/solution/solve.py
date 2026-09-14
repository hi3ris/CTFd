#!/usr/bin/env python3
"""Traverse the entity graph along VERIFIED links only, from the seed persona,
and read the flag off the single reachable PERSON node."""

import csv
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

    seen = {SEED}
    q = deque([SEED])
    persons = []
    while q:
        cur = q.popleft()
        if nodes[cur]["type"] == "person":
            persons.append(cur)
        for nxt in adj[cur]:
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)

    assert len(persons) == 1, f"expected 1 person, got {persons}"
    flag = nodes[persons[0]]["note"]
    print(flag)


if __name__ == "__main__":
    main()
